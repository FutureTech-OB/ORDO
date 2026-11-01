"""Fresh, journaled OpenRouter text generation; never chooses Jev actions."""
import json
import math
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from orgabm.openrouter import _NoRedirect
from orgabm.openrouter_reliable import _RetryTransport


def decode_text(kind,raw):
    if kind=='seed':
        if not isinstance(raw,str) or not raw.strip():raise ValueError('Empty generated seed post.')
        return raw.strip()
    data=json.loads(raw)
    text=data.get('reasons' if kind=='reason' else 'message')
    if isinstance(text,list) and all(isinstance(x,str) for x in text):text=''.join(text)
    if not isinstance(text,str) or not text.strip():raise ValueError('Missing generated content.')
    if kind=='post' and str(data.get('will','')).lower()!='yes':raise ValueError('Generator contradicted selected speaking action.')
    return text.strip()


class ContentGenerator:
    endpoint='https://openrouter.ai/api/v1/chat/completions'
    def __init__(self,output,*,model='deepseek/deepseek-v4.1-flash-1017',reasoning='low',cap_usd=40.,max_requests=250000,
                 journals=(),api_key_env='OPENROUTER_API_KEY',offline=False):
        if model!='deepseek/deepseek-v4.1-flash-1017':raise ValueError('This declared experiment pins the content model.')
        if reasoning not in ('off','low','medium','high'):raise ValueError('Declare a supported reasoning setting.')
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True);self.model=model
        self.key=os.environ.get(api_key_env);self.offline=offline
        if not offline and not self.key:raise ValueError('Set '+api_key_env+' in this process.')
        self.cap=cap_usd;self.max_requests=max_requests;self.cost=self.reserved=0.
        # Reserve at the highest published time-of-day tier, not the currently cheap tier.
        self.price=.30/1e6;self.completion_price=1.2/1e6
        self.reasoning=reasoning;self.max_tokens=256 if reasoning=='off' else 4096
        self.started=self.completed=self.retry_attempts=self.transport_failures=0;self.failed=False
        self.timeout=90;self.max_retries=3;self.backoff_base=1.;self.jitter=.25;self.max_retry_delay=60
        self.lock=threading.Lock();self.opener=_RetryTransport(self,urllib.request.build_opener(_NoRedirect))
        self.recovered=0;self.cache={};self.input_tokens=self.output_tokens=0
        for journal in journals:
            for line in Path(journal).read_text(encoding='utf-8').splitlines():
                row=json.loads(line);eid=row['event_id']
                if row['request']['model']!=model:raise ValueError('Content journal model mismatch.')
                value=decode_text(row['kind'],row['response']['choices'][0]['message']['content'])
                if eid in self.cache and self.cache[eid]['request']!=row['request']:
                    raise ValueError('Duplicate content event with different input.')
                self.cache.setdefault(eid,dict(row,value=value))

    def generate(self,event_id,kind,prompt):
        request=dict(model=self.model,messages=[dict(role='user',content=prompt)],temperature=1,
                     max_tokens=self.max_tokens,reasoning=(dict(enabled=False) if self.reasoning=='off' else dict(effort=self.reasoning)))
        if kind!='seed':request['response_format']=dict(type='json_object')
        if event_id in self.cache:
            row=self.cache[event_id]
            if row['kind']!=kind or row['request']!=request:raise ValueError('Content recovery inputs changed.')
            with self.lock:self.recovered+=1
            return row['value']
        if self.offline:raise ValueError('Offline journal is missing generated event '+event_id)
        body=json.dumps(request,ensure_ascii=True).encode();reserve=len(body)*self.price+self.max_tokens*self.completion_price
        with self.lock:
            if self.failed:raise RuntimeError('Another content request failed.')
            if self.started>=self.max_requests or self.cost+self.reserved+reserve>self.cap:
                raise ValueError('Content generation allowance reached before request.')
            self.started+=1;self.reserved+=reserve
        req=urllib.request.Request(self.endpoint,data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
        start=time.perf_counter()
        try:
            with self.opener.open(req,timeout=self.timeout) as response:raw=json.load(response)
            row=dict(event_id=event_id,kind=kind,request=request,response=raw,elapsed_s=time.perf_counter()-start)
            with self.lock:
                with (self.output/'content_calls.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps(row,ensure_ascii=False).replace(self.key,'[redacted]')+'\n')
            if raw.get('model')!=self.model:raise ValueError('Unexpected generated model; response retained.')
            usage=raw.get('usage',{});cost=usage.get('cost')
            if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:raise ValueError('Content provider cost missing.')
            with self.lock:
                self.cost+=cost;self.reserved-=reserve;self.completed+=1
                self.input_tokens+=usage.get('prompt_tokens',0);self.output_tokens+=usage.get('completion_tokens',0)
            if raw['choices'][0].get('finish_reason')!='stop':raise ValueError('Content was not completed normally; no truncated text enters state.')
            value=decode_text(kind,raw['choices'][0]['message']['content'])
            self.cache[event_id]=dict(row,value=value)
            return value
        except BaseException:
            with self.lock:self.failed=True
            raise

    def usage(self):
        return dict(model=self.model,reasoning=self.reasoning,attempted_requests=self.started,successful_responses=self.completed,
                    recorded_input_cost_usd=self.cost,outstanding_or_uncertain_cost_reserve_usd=self.reserved,
                    input_tokens=self.input_tokens,output_tokens=self.output_tokens,
                    recovered_exact_original_events=self.recovered,retries=self.retry_attempts,
                    transport_failures=self.transport_failures,offline=self.offline,
                    cost_source='provider usage.cost, no headers/credentials in journals',
                    role='Fresh conditional reasons and persuasive posts; Jev owns the sampled discrete actions.')
