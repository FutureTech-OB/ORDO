"""Fresh, bounded batches of decisions. No cross-agent probability cache."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request


class JevEngine:
    def __init__(self, output, cap_usd=0.1, batch_size=64, concurrency=4):
        self.key = os.environ.get('TYPESAFE_API_KEY')
        if not self.key:
            raise ValueError('Set TYPESAFE_API_KEY in the process environment for a live run.')
        self.output = Path(output)
        self.cap = cap_usd
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.model = 'jev-1.14.0'
        self.price = 0.042 / 1_000_000
        self.cost = 0.0
        self.reserved = 0.0
        self.input_tokens = 0
        self.requests = 0
        self.lock = threading.Lock()

    def _call(self, state, questions):
        payload = dict(model=self.model, state=state, questions=questions)
        body = json.dumps(payload, ensure_ascii=True).encode()
        reserve = len(body) * self.price
        with self.lock:
            if self.cost + self.reserved + reserve > self.cap:
                raise ValueError('Client spending guard reached; no further requests submitted.')
            self.reserved += reserve
        request = urllib.request.Request('https://api.typesafe.ai/v1/systemone', data=body,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read())
        except Exception:
            # No automatic retry after ambiguous failures; billing may already have occurred.
            raise RuntimeError('Decision API request failed. Partial logs retained; billing may include the failed request.') from None
        with self.lock:
            with (self.output / 'calls.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(dict(request=payload, response=result,
                    elapsed_s=time.perf_counter()-start), ensure_ascii=False) + '\n')
            usage = result.get('usage', {}).get('input_tokens')
            if type(usage) is not int or usage < 0:
                raise ValueError('Missing or invalid usage; stopping this run.')
            self.input_tokens += usage
            self.cost += usage * self.price
            self.reserved -= reserve
            self.requests += 1
        if result.get('model') != self.model:
            raise ValueError('Unexpected model version in response.')
        answers = result.get('answers', {})
        if set(answers) != set(questions):
            raise ValueError('Response IDs differ from request IDs.')
        out = {}
        for qid, answer in answers.items():
            probs = answer.get('probabilities', {})
            if set(probs) != set(questions[qid]['criteria']):
                raise ValueError('Action keys differ from allowed actions.')
            if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()):
                raise ValueError('Invalid probability value.')
            if abs(sum(probs.values())-1) > 0.005*len(probs) + 1e-9:
                raise ValueError('Invalid probability mass.')
            out[qid] = probs
        return out

    def decide(self, state, questions):
        items = list(questions.items())
        batches = [dict(items[i:i+self.batch_size]) for i in range(0, len(items), self.batch_size)]
        result = {}
        # Completion of every batch is a barrier before any state mutation.
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = [pool.submit(self._call, state, batch) for batch in batches]
            for future in futures:
                result.update(future.result())
        return result

    def usage(self):
        return dict(input_tokens=self.input_tokens, recorded_input_cost_usd=self.cost,
                    successful_requests=self.requests, price_per_million_input_tokens=self.price*1_000_000,
                    accounting='Returned usage only; an ambiguous failed request may also be billed.')
