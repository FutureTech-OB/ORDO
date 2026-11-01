"""One-shot offline completion stage for an already running hybrid experiment.

Does not submit inference, retry inference, schedule jobs, or modify the frozen run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.nc_polarization_live.analyze import analyze
from orgabm.sdk import validate_decisions


def audit_receipts(root,verification):
    models={};questions={};content={};costs=dict(jev=0.,content=0.);requests=dict(jev=0,content=0)
    manifest=[]
    for pattern,kind in [('calls-*/openrouter_calls.jsonl','jev'),('content-*/content_calls.jsonl','content')]:
        for file in sorted(root.glob(pattern)):
            h=hashlib.sha256()
            with file.open('rb') as stream:
                for line in stream:
                    h.update(line);row=json.loads(line);response=row['response'];request=row['request']
                    costs[kind]+=response['usage']['cost'];requests[kind]+=1
                    models[response['model']]=models.get(response['model'],0)+1
                    if kind=='jev':
                        validate_decisions(request['questions'],{q:a['probabilities'] for q,a in response['answers'].items()})
                        for q,qdata in request['questions'].items():
                            fingerprint=hashlib.sha256(json.dumps([request['state'],qdata],sort_keys=True).encode()).digest()
                            if q in questions and questions[q]!=fingerprint:raise ValueError('Jev event changed inputs.')
                            questions[q]=fingerprint
                    else:
                        if request['model']!='deepseek/deepseek-v4.1-flash-1017' or request['reasoning']!={'effort':'low'}:
                            raise ValueError('A generation request did not use the agreed model / low reasoning.')
                        if response['model']!=request['model']:raise ValueError('Wrong returned content model.')
                        eid=row['event_id']
                        fingerprint=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).digest()
                        if eid in content and content[eid]!=fingerprint:raise ValueError('Content event changed inputs.')
                        content[eid]=fingerprint
            manifest.append(dict(path=file.relative_to(root).as_posix(),bytes=file.stat().st_size,sha256=h.hexdigest()))
    counts=verification['cumulative_counts'];expected_jev=sum(counts[k] for k in ('opinion_updates','relationship_decisions','speaking_decisions'))
    expected_content=sum(counts[k] for k in ('seed_posts','opinion_updates','generated_posts'))
    if len(questions)!=expected_jev or len(content)!=expected_content:raise ValueError('Unique fresh event counts do not match state updates.')
    for kind in costs:
        if abs(costs[kind]-verification['total_usage'][kind+'_cost'])>1e-8:raise ValueError('Reported costs differ from provider receipts.')
    return dict(status='verified',unique_jev_decisions=len(questions),unique_content_events=len(content),
        successful_requests=requests,provider_reported_costs_usd=costs,returned_models=models,
        all_content_requests_low_reasoning=True,receipt_files=manifest)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    p.add_argument('--wait',action='store_true');p.add_argument('--max-wait-seconds',type=int,default=14400)
    a=p.parse_args();root=Path(a.run);start=time.monotonic()
    while True:
        try:verification=json.loads((root/'verification.json').read_text(encoding='utf-8'))
        except json.JSONDecodeError:verification=dict(status='running')
        if verification['status']!='running':break
        if not a.wait:raise ValueError('Experiment is still running.')
        if time.monotonic()-start>a.max_wait_seconds:raise TimeoutError('Completion stage timed out; no inference was stopped.')
        time.sleep(15)
    if verification['status']!='complete':
        print(json.dumps(dict(status='experiment_not_complete',verification=verification.get('error_type'),
            paid_inference_restarted=False)),flush=True);return
    plan=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
    for path,sha in plan['source_hashes'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha:raise ValueError('Frozen source changed: '+path)
    receipt_audit=audit_receipts(root,verification)
    (root/'receipt_audit.json').write_text(json.dumps(receipt_audit,indent=2)+'\n',encoding='utf-8')
    summary=analyze(root)
    out=Path('docs/nc_polarization_live/results');out.mkdir(parents=True,exist_ok=True)
    for name in ('plan-before-calls.json','verification.json','trajectory.json','comparison.csv','analysis.json','comparison.png','receipt_audit.json'):
        if (root/name).exists():shutil.copyfile(root/name,out/name)
    same=summary['same_direction_neutral_and_polarization']
    text=('# Network polarization: completed hybrid run\n\n'
        'One world with 1,000 members and 40 epochs. Jev choices and DeepSeek V4.1 Flash 1017 content with low reasoning.\n\n'
        f"- Full input, probability, content and final-state replay: passed.\n"
        f"- Fresh Jev choices: {receipt_audit['unique_jev_decisions']:,}; content events: {receipt_audit['unique_content_events']:,}.\n"
        f"- Successful-response cost: ${summary['actual_cost_usd']:.6f}; components are in analysis.json.\n"
        f"- Neutral-share decline and mean-absolute-opinion increase match the source direction: {'yes' if same else 'no'}.\n\n"
        'The comparison uses one new hybrid-model world. Numerical endpoints and source-model differences are retained in the full comparison.\n\n'
        '[Comparison](analysis.json) · [Trajectories](comparison.csv) · [Receipt audit](receipt_audit.json) · [Methods](../README.md)\n')
    (out/'README.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(status='completed_and_exported',output=str(out),analysis=summary),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
