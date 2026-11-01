"""Verify live receipts and export compact, credential-free cookbook evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    output=Path('docs/jev_validation');output.mkdir(exist_ok=True)
    groups=[]
    for group in ('nc','ncs','sa'):
        root=Path(f'runs/jev-{group}-20261030')
        report=load(root/'verification.json')
        if report['status']!='complete':
            raise ValueError(f'{group} is not complete; do not export it as completed evidence.')
        events=set();submissions=requests=0;cost=0.;models=set();by_paper=Counter()
        for file in sorted(root.glob('calls-*/openrouter_calls.jsonl')):
            for line in file.read_text(encoding='utf-8').splitlines():
                row=json.loads(line);request=row['request'];response=row['response']
                if response['model']!='typesafe/jev-1.14-20261014':
                    raise ValueError('Unexpected returned model version.')
                requests+=1;models.add(response['model']);cost+=response['usage']['cost']
                for qid in request['questions']:
                    if qid in events:raise ValueError('Duplicate successful fresh event ID.')
                    events.add(qid);submissions+=1
        cases=load(root/'case_results.json')
        for case in cases:by_paper[case['paper_id']]+=case['result']['decisions']
        if submissions!=report['fresh_decisions_in_completed_run'] or sum(by_paper.values())!=submissions:
            raise ValueError('Live receipts do not account for completed decisions.')
        if abs(cost-report['total_reported_cost_usd'])>1e-9:
            raise ValueError('Receipt cost differs from aggregate usage.')
        if not report['offline_replay_all_inputs_and_metrics_exact']:
            raise ValueError('Replay is not verified.')
        for name,sha in report['source_hashes'].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:
                raise ValueError(f'Frozen source changed: {name}')
        row=dict(group=group,papers=report['paper_ids'],worlds=len(cases),
            fresh_choice_distributions=submissions,successful_http_requests=requests,
            attempted_http_requests=report['total_attempted_requests'],
            provider_reported_cost_usd=cost,models_returned=sorted(models),
            elapsed_s_final_attempt_including_analysis_and_replay=report['elapsed_s_this_attempt'],
            summed_attempt_elapsed_s_including_failures_and_replay=report['elapsed_s_this_attempt']+sum(
                load(p)['elapsed_s_this_attempt'] for p in root.glob('verification-interrupted-*.json')),
            choices_by_paper=dict(by_paper),exact_offline_input_and_metric_replay=True,
            uncertainty_reserve_usd=report['total_uncertain_reserve_usd'],
            source_verification=(root/'verification.json').as_posix())
        groups.append(row)
        save(output/f'{group}_analysis.json',load(root/'analysis.json'))
        save(output/f'{group}_plan.json',load(root/'plan-before-calls.json'))
        if (root/'metadata-normalization-recovery.json').exists():
            fix=load(root/'metadata-normalization-recovery.json')
            helper=Path('tools/resume_jev_normalized.py')
            if fix['helper_sha256']!=hashlib.sha256(helper.read_bytes()).hexdigest():
                raise ValueError('Recovery helper changed.')
            save(output/f'{group}_recovery_metadata.json',fix)
    result=dict(status='complete',scope='Fresh Jev execution of nine paper-derived ABM protocols; not nine successful full-paper replications.',
        groups=groups,papers=sum(len(g['papers']) for g in groups),worlds=sum(g['worlds'] for g in groups),
        fresh_choice_distributions=sum(g['fresh_choice_distributions'] for g in groups),
        successful_http_requests=sum(g['successful_http_requests'] for g in groups),
        attempted_http_requests=sum(g['attempted_http_requests'] for g in groups),
        provider_reported_cost_usd=sum(g['provider_reported_cost_usd'] for g in groups),
        costs_exclude='Connectivity probe, prior experiments, and any unreported charges for failed attempts.',
        units='Cases can contain independent colonies/pairs; fresh questions need not be distinct behavioral opportunities when alternatives coincide.',
        native_batch=True,probability_reuse=False,all_offline_replays_exact=True)
    save(output/'coverage.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
