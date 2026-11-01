"""Native Jev decision batches on OpenRouter; no chat-completion routing."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request

from .sdk import validate_decisions


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise RuntimeError('Credential-bearing decision requests cannot follow redirects.')


class OpenRouterJevEngine:
    endpoint='https://openrouter.ai/api/alpha/decisions'

    def __init__(self,output,*,model='typesafe/jev-1.14',cap_usd=0.01,
                 batch_size=64,concurrency=1,max_requests=100,api_key_env='OPENROUTER_API_KEY'):
        if model not in ('typesafe/jev-1.14','typesafe/jev-1.13'):
            raise ValueError('Choose a pinned Jev decision-model family, not a router or latest alias.')
        if any(type(x) is not int or x<1 for x in (batch_size,concurrency,max_requests)) or concurrency>32:
            raise ValueError('Positive batch/request limits and concurrency <=32 are required.')
        if type(cap_usd) not in (int,float) or not math.isfinite(cap_usd) or cap_usd<=0:
            raise ValueError('A finite positive client cost allowance is required.')
        self.key=os.environ.get(api_key_env)
        if not self.key: raise ValueError(f'Set {api_key_env} in the process environment.')
        self.output=Path(output); self.output.mkdir(parents=True,exist_ok=True)
        self.model=model; self.cap=cap_usd; self.batch_size=batch_size
        self.concurrency=concurrency; self.max_requests=max_requests
        self.price=0.042/1_000_000  # Provider list price checked 2026-10-29; actual usage.cost is retained.
        self.cost=self.reserved=0.0; self.input_tokens=self.output_tokens=0
        self.started=self.completed=0; self.failed=False; self.returned_models=set()
        self.latencies=[]; self.lock=threading.Lock()
        self.opener=urllib.request.build_opener(_NoRedirect)

    def _call(self,state,questions):
        body=json.dumps(dict(model=self.model,state=state,questions=questions),ensure_ascii=True).encode()
        reservation=len(body)*self.price
        with self.lock:
            if self.failed: raise RuntimeError('An earlier ambiguous/invalid request stopped this engine.')
            if self.started>=self.max_requests or self.cost+self.reserved+reservation>self.cap:
                raise ValueError('Client request or spending allowance reached before submission.')
            self.started+=1; self.reserved+=reservation
        request=urllib.request.Request(self.endpoint,data=body,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
        start=time.perf_counter()
        try:
            try:
                with self.opener.open(request,timeout=45) as response: raw=json.loads(response.read())
            except urllib.error.HTTPError as error:
                raise RuntimeError(f'OpenRouter returned HTTP {error.code}; no automatic retry; billing may include this request.') from None
            except Exception:
                raise RuntimeError('OpenRouter request failed; no automatic retry; billing may include this request.') from None
            elapsed=time.perf_counter()-start
            with self.lock:
                # Persist response and request body, never headers or credentials.
                record=json.dumps(dict(endpoint=self.endpoint,request=json.loads(body),response=raw,elapsed_s=elapsed),ensure_ascii=False)
                with (self.output/'openrouter_calls.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(record.replace(self.key,'[redacted]')+'\n')
            model=raw.get('model','')
            if not isinstance(model,str) or not re.fullmatch(re.escape(self.model)+r'(?:-\d{8})?',model):
                raise ValueError('Unexpected returned model family; raw response retained.')
            usage=raw.get('usage',{}); tokens=usage.get('input_tokens'); output=usage.get('output_tokens',0)
            cost=usage.get('cost')
            if type(tokens) is not int or tokens<0 or type(output) is not int or output<0:
                raise ValueError('Missing/invalid token accounting; stopping engine.')
            if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:
                raise ValueError('Missing/invalid provider-reported cost; stopping engine.')
            with self.lock:
                self.cost+=cost; self.reserved-=reservation; self.input_tokens+=tokens; self.output_tokens+=output
                self.completed+=1; self.returned_models.add(model); self.latencies.append(elapsed)
            answers=raw.get('answers',{})
            if not isinstance(answers,dict): raise ValueError('Missing decision answers.')
            return validate_decisions(questions,{qid:a.get('probabilities') if isinstance(a,dict) else None
                                                for qid,a in answers.items()})
        except Exception:
            with self.lock: self.failed=True
            raise

    def decide(self,state,questions):
        if any(q.get('type')!='choice' for q in questions.values()):
            raise ValueError('This ORDO adapter currently exposes categorical choice probabilities only.')
        items=list(questions.items()); result={}
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            jobs=[pool.submit(self._call,state,dict(items[i:i+self.batch_size]))
                  for i in range(0,len(items),self.batch_size)]
            for job in jobs: result.update(job.result())
        return result

    def usage(self):
        return dict(provider='openrouter',endpoint=self.endpoint,model_requested=self.model,
            models_returned=sorted(self.returned_models),native_batch=True,probability_reuse=False,
            attempted_requests=self.started,successful_responses=self.completed,
            input_tokens=self.input_tokens,output_tokens=self.output_tokens,
            recorded_input_cost_usd=self.cost,cost_source='sum of provider usage.cost; not inferred from list price',
            mean_request_latency_s=sum(self.latencies)/len(self.latencies) if self.latencies else None,
            client_max_requests=self.max_requests,client_cap_usd=self.cap,stopped_after_error=self.failed,
            accounting='Client reservations estimate input cost. Failed requests may also be billed; this is not a provider billing cap.')
