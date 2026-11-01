"""Exercise real engine serializers against local fake HTTP responses only."""
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

from orgabm.deepseek import DeepSeekEngine
from orgabm.engines import JevEngine
from orgabm.sdk import run_simulation
from .environments import NamingGame, MajorityOpinion


def verify_interfaces(output):
    root=Path(output); root.mkdir(parents=True,exist_ok=False)
    results=[]
    for provider in ('jev','chat'):
        for scene,make in [('naming',lambda:NamingGame(agents=6)),('opinion',lambda:MajorityOpinion(agents=6))]:
            case=root/f'{provider}-{scene}'; case.mkdir()
            requests=[]
            def jev_response(request,**kwargs):
                body=json.loads(request.data); requests.append(body)
                return io.BytesIO(json.dumps(dict(model='jev-1.14.0',usage={'input_tokens':10},
                    answers={qid:dict(probabilities={k:float(i==0) for i,k in enumerate(q['criteria'])})
                             for qid,q in body['questions'].items()})).encode())
            def chat_response(request,**kwargs):
                body=json.loads(request.data); requests.append(body)
                question=json.loads(body['messages'][1]['content'])
                return io.BytesIO(json.dumps(dict(model='offline-fake-response',
                    choices=[dict(finish_reason='stop',message={'content':json.dumps({'action':next(iter(question['criteria']))})})],
                    usage={'prompt_tokens':10,'completion_tokens':5})).encode())
            with patch.dict(os.environ,{'TYPESAFE_API_KEY':'offline-placeholder','ORDO_OFFLINE_KEY':'offline-placeholder'}):
                if provider=='jev':
                    engine=JevEngine(case,batch_size=64,concurrency=1)
                    with patch('orgabm.engines.urllib.request.urlopen',side_effect=jev_response):
                        run=run_simulation(make(),engine,rounds=4,seed=7,output=case/'run')
                else:
                    engine=DeepSeekEngine(model='offline-placeholder',api_key_env='ORDO_OFFLINE_KEY',
                                          base_url='https://offline.invalid/v1',concurrency=1,output=case)
                    with patch.object(engine.opener,'open',side_effect=chat_response):
                        run=run_simulation(make(),engine,rounds=4,seed=7,output=case/'run')
            sizes=[len(x['questions']) for x in requests] if provider=='jev' else [1]*len(requests)
            expected=([2]*4 if scene=='naming' else [1]*4) if provider=='jev' else [1]*run['decisions']
            if sizes!=expected: raise AssertionError('Interface batching differs from activation protocol.')
            results.append(dict(provider=provider,scene=scene,status=run['status'],
                decisions=run['decisions'],mock_http_requests=len(requests),questions_per_mock_request=sizes,
                actual_network_requests=0,usage_semantics='synthetic test values; not measured tokens or cost'))
    report=dict(mode='mock_transport_real_serializers',actual_network_requests=0,cases=results)
    (root/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
