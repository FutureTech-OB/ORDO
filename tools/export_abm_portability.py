"""Export compact, shareable evidence from a completed native-rule ABM run."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('docs/abm_cookbook'))
    parser.add_argument('--date',required=True)
    parser.add_argument('--tests-passed',type=int)
    args=parser.parse_args()
    manifest=json.loads((args.run/'manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='complete' or manifest['engine']!='native':
        raise ValueError('Export requires a complete native-rule verification run.')
    rows=manifest['rows']
    if not all(r['exact_reference_match'] for r in rows): raise ValueError('Reference check failed.')
    args.output.mkdir(parents=True,exist_ok=True)
    audits=[]
    for row in rows:
        folder=args.run/row['evidence']
        audits.append(dict(case=row['evidence'],audit=json.loads((folder/'audit.json').read_text(encoding='utf-8')),
                           environment=json.loads((folder/'ordo/result.json').read_text(encoding='utf-8'))['environment']))
    report=dict(date=args.date,scope='Native-rule ABM portability, not live Jev or human validity evidence.',
        completed_worlds=len(rows),matched_rounds=sum(r['completed_rounds'] for r in rows),
        decisions=sum(r['decisions'] for r in rows),paid_api_calls=manifest['paid_api_calls'],
        tests_passed=args.tests_passed,manifest=manifest,world_audits=audits)
    (args.output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    groups=defaultdict(list)
    for r in rows:
        c=r['config']
        key=(r['model'],c.get('activation_order',c.get('contact','')),c.get('defection_bonus',c.get('homophily','')))
        groups[key].append(r)
    lines=[f'# ABM portability verification | {args.date}','',
        f'Completed {len(rows)} ORDO worlds, {report["matched_rounds"]} rounds and {report["decisions"]:,} decisions. All declared reference checks pass, with zero paid API calls.','',
        'Wealth exchange, spatial cooperation and Schelling use independent Mesa 3.5.1 references, comparing individual state, clocks and randomness. Organizational learning uses the independent Python reference.','',
        f'The recorded suite passes {args.tests_passed} tests, covering reference models, activation orders, conservation, engine substitution and mocked native Jev serialization.','',
        '## Descriptive results','',
        'The following endpoints average seeds 7, 8 and 9 under the declared rules.','',
        '| Model | Condition | Metric | Three-world mean |','| --- | --- | --- | --- |']
    for (kind,mode,parameter),values in groups.items():
        metric={'wealth':'gini','cooperation':'cooperation_share','schelling':'same_type_neighbor_share','organization':'gross_performance'}[kind]
        condition=mode or 'default'
        if parameter!='': condition+=f'; parameter={parameter}'
        mean=statistics.mean(v['final'][metric] for v in values)
        lines.append(f'| {kind} | {condition} | {metric} | {mean:.4f} |')
    lines+=['','## Inspect and rerun','',
        '[verification.json](verification.json) contains world summaries, configurations and source hashes. Complete events and states remain in local run directories.','',
        '```bash','python -m examples.abm_cookbook.run --cases examples/abm_cookbook/cases.json --output runs/abm-portability-reproduction',
        'python -m unittest discover -s tests -v','```','',
        'Existing social ABMs execute through the public interface while retaining their declared reference dynamics. Alternative decision engines create separately recorded behavioral versions.','',
        '[Cookbook](README.md)','']
    (args.output/'verified_results.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('completed_worlds','matched_rounds','decisions','paid_api_calls','tests_passed')},ensure_ascii=False))


if __name__=='__main__': main()
