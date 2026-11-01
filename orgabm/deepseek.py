"""Bring-your-own-key DeepSeek decisions; independent requests, bounded concurrency.

This is not native batch inference. Default output is one chosen action, encoded
as a one-hot distribution. Optional elicited probabilities are not token likelihoods.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from .sdk import validate_decisions


class NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('Credential-bearing API requests cannot follow redirects.')


class DeepSeekEngine:
    def __init__(self, *, model='deepseek-flash', thinking=False, concurrency=4,
                 max_requests=100, max_tokens=1024, output_mode='action', output=None,
                 base_url=None, api_key_env='DEEPSEEK_API_KEY', timeout=60):
        self.key = os.environ.get(api_key_env)
        if not self.key:
            raise ValueError(f'Set {api_key_env} in the local process environment.')
        self.base_url = (base_url or os.environ.get('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com').rstrip('/')
        parsed = urllib.parse.urlsplit(self.base_url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Use an HTTPS base URL without embedded credentials, query or fragment.')
        if self.base_url.endswith('/chat/completions'):
            raise ValueError('Supply a base URL such as https://host/v1, without /chat/completions.')
        self.endpoint = self.base_url+'/chat/completions'
        if type(timeout) not in (int,float) or not 0 < timeout <= 180:
            raise ValueError('timeout must be between 0 and 180 seconds.')
        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoCredentialRedirect)
        if output_mode not in ['action', 'distribution']:
            raise ValueError('Choose action or distribution output.')
        if any(type(x) is not int or x < 1 for x in [concurrency,max_requests,max_tokens]) or concurrency > 32:
            raise ValueError('Invalid request limits.')
        self.model, self.thinking = model, thinking
        self.concurrency, self.max_requests, self.max_tokens = concurrency,max_requests,max_tokens
        self.output_mode, self.output = output_mode, Path(output) if output else None
        if self.output:
            self.output.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.started = self.completed = self.input_tokens = self.output_tokens = 0
        self.returned_models = set()
        self.latencies = []

    def request_payload(self, state, question):
        example = {'action': next(iter(question['criteria']))} if self.output_mode == 'action' else {
            'probabilities': {key: 1/len(question['criteria']) for key in question['criteria']}}
        instruction = ('Choose this agent\'s next action.' if self.output_mode == 'action' else
                       'Estimate this agent\'s action distribution; probabilities must sum to one.')
        return dict(model=self.model, messages=[
            dict(role='system', content=state+'\n'+instruction+' Return only JSON in this format: '+json.dumps(example)),
            dict(role='user', content=json.dumps(question, ensure_ascii=False))],
            response_format={'type':'json_object'}, thinking={'type':'enabled' if self.thinking else 'disabled'},
            max_tokens=self.max_tokens, stream=False)

    def _call(self, qid, state, question):
        payload = self.request_payload(state, question)
        request = urllib.request.Request(self.endpoint,
            data=json.dumps(payload).encode(), headers={'Content-Type':'application/json',
                'Authorization':'Bearer '+self.key})
        started = time.perf_counter()
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'Decision API returned HTTP {error.code}; no retry; the request may have been billed.') from None
        except Exception:
            raise RuntimeError('DeepSeek request failed; no automatic retry; the request may have been billed.') from None
        elapsed = time.perf_counter()-started
        with self.lock:
            if self.output:
                with (self.output/'deepseek_calls.jsonl').open('a', encoding='utf-8') as stream:
                    record=json.dumps(dict(id=qid,endpoint=self.endpoint,request=payload,response=raw,elapsed_s=elapsed),ensure_ascii=False)
                    stream.write(record.replace(self.key,'[redacted]')+'\n')
            self.completed += 1
            self.latencies.append(elapsed)
            if isinstance(raw.get('model'),str):
                self.returned_models.add(raw['model'])
            self.input_tokens += raw.get('usage',{}).get('prompt_tokens',0)
            self.output_tokens += raw.get('usage',{}).get('completion_tokens',0)
        choice = raw['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError('Incomplete DeepSeek response; round will not advance.')
        content = json.loads(choice['message']['content'])
        if self.output_mode == 'action':
            action = content.get('action')
            if action not in question['criteria']:
                raise ValueError('DeepSeek returned an unavailable action.')
            p = {k: float(k == action) for k in question['criteria']}
        else:
            p = content.get('probabilities')
        return validate_decisions({qid:question},{qid:p})[qid]

    def decide(self, state, questions):
        with self.lock:
            if self.started+len(questions)>self.max_requests:
                raise ValueError('Request cap would be exceeded; this round was not sent.')
            self.started += len(questions)
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {qid: pool.submit(self._call,qid,state,q) for qid,q in questions.items()}
            return {qid: future.result() for qid,future in futures.items()}

    def usage(self):
        return dict(model_requested=self.model, models_returned=sorted(self.returned_models),
                    base_url=self.base_url, thinking=self.thinking, native_batch=False,
                    requests_reserved=self.started, successful_requests=self.completed,
                    input_tokens=self.input_tokens, output_tokens=self.output_tokens,
                    mean_request_latency_s=sum(self.latencies)/len(self.latencies) if self.latencies else None,
                    probability_semantics='sampled_action' if self.output_mode=='action' else 'elicited_distribution',
                    note='No dollar-cost estimate; returned model/version and provider usage are retained in call logs.')
