"""Export verified reduced native-CMM evidence; no network or model API calls."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean


def export(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Only complete runs can be exported.')
    for path,expected in report['source_hashes'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Experiment source changed: '+path)
    if not all(r['all_period_metrics_and_state_hashes_exact'] and r['full_final_state_exact'] for r in report['cases']):
        raise ValueError('A reference audit did not pass.')
    report['source_hashes']={Path(k).resolve().relative_to(Path.cwd()).as_posix():v for k,v in report['source_hashes'].items()}
    report['build']=json.loads((root/'build_manifest.json').read_text(encoding='utf-8'))
    report['upstream']=json.loads((root/'source_manifest.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for row in report['cases']:
        c=row['config'];groups[(c['agents'],c['memory'],c['rho0'])].append(row)
    summary=[]
    for (n,memory,rho0),rows in groups.items():
        summary.append(dict(agents=n,memory=memory,rho0=rho0,seeds=len(rows),
            occupied_sites_mean=mean(r['final']['occupied_sites'] for r in rows),
            radius_mean=mean(r['final']['mean_toroidal_radius'] for r in rows),
            spatial_concentration_mean=mean(r['final']['spatial_concentration'] for r in rows)))
    report['summary']=summary
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'results.csv').write_bytes((root/'summary.csv').read_bytes())
    lines=['# Mobility source-kernel results','',
        f"Completed {len(report['cases'])} worlds and {report['sdk_control_actions']} native periods, with {report['native_agent_updates']:,} individual updates. The SDK records {report['sdk_control_actions']} whole-period control actions, with zero model API requests.",'',
        '| Population | Memory | rho0 | Seeds | Mean occupied locations | Mean toroidal radius | Mean concentration |',
        '| ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for row in summary:
        lines.append(f"| {row['agents']} | {row['memory']} | {row['rho0']:g} | {row['seeds']} | {row['occupied_sites_mean']:.2f} | {row['radius_mean']:.3f} | {row['spatial_concentration_mean']:.5f} |")
    lines+=['','All period metrics and complete state fingerprints match independent native processes. Final vectors, population totals, movement accounts and enabled visit-frequency conservation pass.','',
        'The finite suite uses a 300×300 grid and 40 periods, varying rho0 and memory. When memory is off, the original visit counter is not updated; mean_memory_locations describes stored counts.','',
        f"Total runtime is {report['elapsed_s']:.2f} seconds, including both execution paths, state export and verification.",'',
        '[Results](results.json) · [World CSV](results.csv) · [Methods and build](README.md)','']
    (out/'results.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(worlds=len(report['cases']),native_agent_updates=report['native_agent_updates'],
        sdk_control_actions=report['sdk_control_actions'],all_exact=True,elapsed_s=report['elapsed_s']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,default=Path('docs/ncs_mobility'))
    a=p.parse_args();export(a.run,a.output)
