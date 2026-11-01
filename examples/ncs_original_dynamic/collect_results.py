"""Read complete native repeats and report only genuinely complete ten-run points."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean,stdev


def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder');args=parser.parse_args()
    root=Path(args.folder);plan=json.loads((root/'plan.json').read_text());status=json.loads((root/'status.json').read_text())
    references=json.loads(Path(__file__).with_name('author_reference.json').read_text())
    results={p.name[:-len('.result.json')]:json.loads(p.read_text()) for p in root.glob('*.result.json')}
    points=[]
    for ref in references:
        group=[v for v in results.values() if v['np']==ref['np'] and v['delta']==ref['delta'] and v['network']==ref['network']]
        values=[v['cooperation_frequency'] for v in group]
        row=dict(delta=ref['delta'],periphery=ref['np'],network=ref['network'],
            completed_repeats=len(values),required_repeats=10,status='complete' if len(values)==10 else 'incomplete',
            author_reference_frequency=ref['author_frequency'],reference_source=ref['source_file'])
        if len(values)==10:
            row.update(mean_cooperation=mean(values),repeat_sd=stdev(values),repeat_se=stdev(values)/len(values)**.5,
                difference_from_author_reference=mean(values)-ref['author_frequency'],total_events=1_000_000_000,
                max_normalization_roundoff=max(abs(v['cooperation_frequency']+v['defection_frequency']-1) for v in group))
        points.append(row)
    running_progress=[]
    for job in status['running']:
        file=root/(job['id']+'.progress.jsonl')
        if file.exists():
            lines=file.read_text().splitlines()
            if lines:running_progress.append(dict(job,**json.loads(lines[-1])))
    report=dict(status='complete' if len(results)==len(plan['jobs']) and not status['failed'] else 'running' if status['status']=='running' else 'incomplete',
        evidence='Full-length native Julia Simulation.jl with published graph-construction reconstruction; not Jev',
        doi=plan['doi'],complete_repeats=len(results),required_repeats=len(plan['jobs']),
        complete_points=sum(p['status']=='complete' for p in points),required_points=len(points),
        complete_native_events=sum(v['iterations'] for v in results.values()),api_calls=0,paid_cost_usd=0,
        all_finished_repeats_full_length=all(v['iterations']==100_000_000 for v in results.values()),
        all_finished_repeats_original_burnin=all(v['burnin_iterations']==5_000_000 for v in results.values()),
        all_finished_instrumentation_checks_exact=all(v['instrumentation_exact_test'] for v in results.values()),
        source_sha256=hashlib.sha256(Path(__file__).with_name('upstream').joinpath('Simulation.jl').read_bytes()).hexdigest(),
        coordinator=status,points=points,running_progress=running_progress,
        comparison_scope='Independent seeds; compare means and Monte Carlo dispersion to archived source values, not exact unseeded trajectory equality.')
    (root/'verification.snapshot.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('points','coordinator','running_progress')},indent=2))


if __name__=='__main__':main()
