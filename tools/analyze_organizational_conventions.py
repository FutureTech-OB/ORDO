"""Export the organizational convention factorial comparison and scientific figures."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys


def condition(config):return config['placement']+' / '+config['message_mode']


def read_events(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:yield json.loads(line)


def paths_for(report):
    return {provider:report.get('active_jev_trace','jev') if provider=='jev' else provider for provider in report['groups']}


def validate_and_replay(root,report,frozen):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from orgabm.sdk import run_simulation
    from examples.organizational_conventions.run import make_worlds
    from examples.organizational_conventions.model import OrganizationEnsemble
    for file,sha in report['source_hashes'].items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=sha:
            raise ValueError('Experiment source differs from the recorded version.')
    audits={}; periods=frozen['preview']['periods']
    for provider,trace in paths_for(report).items():
        original=json.loads((root/trace/'result.json').read_text(encoding='utf-8'))
        if original['status']!='complete':raise ValueError('Do not treat a partial trajectory as completed evidence.')
        class Tape:
            def __init__(self,stream):self.stream=stream
            def decide(self,state,questions):
                row=json.loads(next(self.stream))
                if state!=row['state'] or questions!=row['questions']:raise AssertionError('Local observations differ on replay.')
                return row['probabilities']
            def usage(self):return {'engine':'offline-recorded-probabilities','actual_model_api_calls':0}
        worlds=make_worlds(frozen['configs']);env=OrganizationEnsemble(worlds)
        with (root/trace/'events.jsonl').open(encoding='utf-8') as stream:
            replay=run_simulation(env,Tape(stream),rounds=periods,seed=202610)
            if next(stream,None) is not None:raise AssertionError('Unconsumed trace records.')
        if replay['metrics']!=original['metrics']:raise AssertionError('Replayed organizational metrics differ.')
        # Contacts and people are the same across factorial treatments within a seed.
        for step in replay['metrics']:
            grouped=defaultdict(set)
            for wid,row in step['worlds'].items():grouped[frozen['configs'][wid]['seed']].add(row['schedule_sha256'])
            if any(len(v)!=1 for v in grouped.values()):raise AssertionError('Treatment changed contact opportunities.')
        rows=report['groups'][provider]['worlds']; by_seed=defaultdict(list)
        for row in rows:by_seed[row['config']['seed']].append(row)
        for cohort in by_seed.values():
            if len({r['environment']['structure_sha256'] for r in cohort})!=1 or len({r['environment']['population_sha256'] for r in cohort})!=1:
                raise AssertionError('Population or reporting structure changed between treatments.')
        snapshots=root/('jev-snapshots' if provider=='jev' else f'{provider}-snapshots')
        for wid,world in worlds.items():
            saved=json.loads((snapshots/f'{wid}.json').read_text(encoding='utf-8'))
            rebuilt=json.loads(json.dumps(world.snapshot(),ensure_ascii=False,allow_nan=False))
            if saved!=rebuilt:raise AssertionError('Full final individual state differs on replay.')
        for placement in ('employee','manager'):
            for seed in by_seed:
                peers=[r for r in rows if r['config']['placement']==placement and r['config']['seed']==seed and r['config']['message_mode'] in ('peer','official')]
                if len(peers)!=2:raise AssertionError('Expected paired peer/official information treatments.')
                a,b=[json.loads((snapshots/f"{r['world']}.json").read_text(encoding='utf-8')) for r in peers]
                if a['bulletin_exposures']!=b['bulletin_exposures']:raise AssertionError('Message exposure differs between peer and official treatment.')
        audits[provider]=dict(all_inputs_exact=True,all_metrics_exact=True,people_and_structure_matched=True,
            contact_schedules_matched=True,peer_official_exposures_matched=True,actual_model_api_calls=0,
            full_final_states_exact=True,decisions=replay['decisions'],periods=periods)
    return audits


def grouped_results(report):
    result={}
    for provider,group in report['groups'].items():
        groups=defaultdict(list)
        for row in group['worlds']:groups[condition(row['config'])].append(row)
        result[provider]={}
        for label,rows in groups.items():
            last=[r['last'] for r in rows]
            result[provider][label]=dict(worlds=len(rows),members=rows[0]['config']['agents'],
                voluntary_M_share=mean(r['voluntary_M_share'] for r in last),
                voluntary_M_range=[min(r['voluntary_M_share'] for r in last),max(r['voluntary_M_share'] for r in last)],
                targeted_department_M_share=mean(r['targeted_department_M_share'] for r in last),
                untargeted_department_M_share=mean(r['untargeted_department_M_share'] for r in last),
                coordination=mean(r['coordination'] for r in last),
                ordinary_coverage=mean(r['ordinary_coverage'] for r in last),
                ordinary_bulletin_readers=mean(r['ordinary_bulletin_readers'] for r in last),
                seed_contact_count=mean(r['seed_contact_count'] for r in last),
                seed_encounters=mean(r['seed_encounters'] for r in rows))
    return result


def plot_and_csv(root,out,report):
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists():sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    datasets={};configs=report['frozen_plan']['configs']
    with (out/'trajectories.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['engine','world','seed','placement','message_mode','period','voluntary_M_share','target_department_M_share','other_department_M_share','coordination','coverage','seed_contacts'])
        for provider,trace in paths_for(report).items():
            data=defaultdict(list)
            for event in read_events(root/trace/'events.jsonl'):
                for wid,row in event['metrics']['worlds'].items():
                    data[wid].append(row);c=configs[wid]
                    writer.writerow([provider,wid,c['seed'],c['placement'],c['message_mode'],row['period'],row['voluntary_M_share'],
                        row['targeted_department_M_share'],row['untargeted_department_M_share'],row['coordination'],row['ordinary_coverage'],row['seed_contact_count']])
            datasets[provider]=data
    with (out/'world_summary.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['engine','world','seed','placement','message_mode','members','periods','voluntary_M_share','coordination','coverage','seed_contacts'])
        for provider,group in report['groups'].items():
            for r in group['worlds']:
                c=r['config'];last=r['last']
                writer.writerow([provider,r['world'],c['seed'],c['placement'],c['message_mode'],c['agents'],r['completed_periods'],
                    last['voluntary_M_share'],last['coordination'],last['ordinary_coverage'],last['seed_contact_count']])
    colors={'none':'#888888','peer':'#009e73','official':'#cc3377'}
    fig,axes=plt.subplots(1,3,figsize=(15.5,4.5),layout='constrained')
    rows=report['groups']['jev']['worlds']
    periods=report['frozen_plan']['preview']['periods']
    max_adoption=0
    for placement,style in [('employee','--'),('manager','-')]:
        for mode in ('none','peer','official'):
            matching=[r for r in rows if r['config']['placement']==placement and r['config']['message_mode']==mode]
            curves=np.array([[v['voluntary_M_share'] for v in datasets['jev'][r['world']]] for r in matching])
            max_adoption=max(max_adoption,float(curves.max()))
            x=np.arange(1,periods+1)
            axes[0].plot(x,curves.mean(axis=0),style,color=colors[mode],label=f'{placement}, {mode}')
            axes[0].fill_between(x,curves.min(axis=0),curves.max(axis=0),color=colors[mode],alpha=.08)
    axes[0].set(title='A  Voluntary adoption (non-fixed members)',xlabel='Organizational period',ylabel='Share whose last choice is M',ylim=(0,min(1,max(.2,max_adoption*1.15))))
    axes[0].legend(fontsize=7)
    labels=['employee / '+m for m in ('none','peer','official')]+['manager / '+m for m in ('none','peer','official')]
    positions=np.arange(6)
    for engine,offset,color in [('jev',-.27,'#1666ad'),('history',-.09,'#888888'),('notice',.09,'#e69f00'),('uniform',.27,'#bbbbbb')]:
        values=[report['summary'][engine][label]['voluntary_M_share'] for label in labels]
        axes[1].bar(positions+offset,values,.17,label=engine,color=color)
    axes[1].set(title='B  Final adoption and explicit-rule controls',ylabel='Non-fixed-member M share',xticks=positions,
        xticklabels=['E:none','E:peer','E:official','M:none','M:peer','M:official'],ylim=(0,1))
    axes[1].tick_params(axis='x',labelrotation=40,labelsize=8);axes[1].legend(fontsize=7)
    targeted=[report['summary']['jev'][label]['targeted_department_M_share'] for label in labels]
    other=[report['summary']['jev'][label]['untargeted_department_M_share'] for label in labels]
    axes[2].bar(positions-.18,targeted,.35,label='Departments containing a fixed member',color='#1666ad')
    axes[2].bar(positions+.18,other,.35,label='Other departments',color='#a6a6a6')
    axes[2].set(title='C  Organizational boundaries',ylabel='Non-fixed-member M share',xticks=positions,
        xticklabels=['E:none','E:peer','E:official','M:none','M:peer','M:official'],ylim=(0,1))
    axes[2].tick_params(axis='x',labelrotation=40,labelsize=8);axes[2].legend(fontsize=7)
    fig.suptitle('1,000 members, 50 departments, 20 fixed M members | two seeds per condition; shading = observed range',fontsize=11)
    fig.savefig(out/'organizational_conventions.png',dpi=180);fig.savefig(out/'organizational_conventions.pdf');plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',default='docs/organizational_conventions/results')
    args=parser.parse_args();root=Path(args.run);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete' or report['groups'].get('jev',{}).get('status')!='complete':
        raise ValueError('A complete live comparison is required; preserve partial runs separately.')
    frozen=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
    report['audit']=validate_and_replay(root,report,frozen)
    report['frozen_plan']=frozen;report['summary']=grouped_results(report)
    report['analysis_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    from tools.replay_organizational_conventions import export_replay,portable_source_hashes
    report['source_hashes']=portable_source_hashes(report['source_hashes'])
    report['replay_tool_source_sha256']=hashlib.sha256(Path('tools/replay_organizational_conventions.py').read_bytes()).hexdigest()
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    export_replay(root,out,report)
    plot_and_csv(root,out,report)
    lines=['# Conventions, positions and publishing permissions in a large organization','','2026-10-29. Each world contains 1,000 members in 50 departments, with executive, manager and employee reporting levels. Twenty members always choose M; 980 choose freely. Six conditions use two seeds each, with the same grid under three rule controls.','',
        '## Jev results','','| Committed-member position | Information condition | Ordinary-member M share | Seeded-department M share | Other-department M share | Final-period coordination |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for label,s in report['summary']['jev'].items():
        placement,mode=label.split(' / ')
        lines.append(f"| {placement} | {mode} | {s['voluntary_M_share']:.1%} | {s['targeted_department_M_share']:.1%} | {s['untargeted_department_M_share']:.1%} | {s['coordination']:.1%} |")
    jm=report['summary']['jev'];official=jm['manager / official'];peer=jm['manager / peer'];worker=jm['employee / official']
    lines+=['','## Findings','',
        f"- Committed members represent 2% of the organization. With formal guidance, ordinary-member M adoption is {worker['voluntary_M_share']:.1%} for employee placement and {official['voluntary_M_share']:.1%} for manager placement. Placement changes contacts and role context together.",
        f"- Under manager placement, peer and formal guidance yield {peer['voluntary_M_share']:.1%} and {official['voluntary_M_share']:.1%}. Content, departmental readers and exposure are matched.",
        f"- Under manager/formal guidance, seeded departments reach {official['targeted_department_M_share']:.1%} and other departments {official['untargeted_department_M_share']:.1%}, showing localized diffusion."]
    lines+=['','Shares use the latest ordinary-member actions and exclude committed members. The placement treatment includes both contact opportunities and role information.','',
        '![Organizational conventions and permissions](organizational_conventions.png)','','## Mechanisms and verification','',
        'Conditions share population and reporting. Contact schedules match within seed. Peer and formal guidance match content, departmental readers and actual exposure; formal guidance additionally requires a validated publishing grant. Members choose voluntarily.','',
        'Each period collects choices from 125 disjoint pairs before simultaneous settlement: 4,000 pairs over 32 periods. Members retain five encounters and read departmental notices under access permissions.','',
        'Controls are uniform random choice, recent-opponent majority history, and notice-following when formal guidance is visible with history otherwise. Two seeds provide an exploratory organizational comparison.','',
        'Q and M have symmetric payoffs. M shares measure diffusion; final-period coordination and full trajectories measure matching. Notices are persistent researcher-configured records.','',
        'All four engines match local inputs, period metrics and complete final individual states under saved-probability replay. Checks also match reporting, contacts and peer/formal notice exposure.','',
        f"Jev returns {report['groups']['jev']['decisions']:,} new choices in {report['usage']['successful_responses']:,} successful responses, with reported cost ${report['usage']['recorded_input_cost_usd']:.6f}. There are {report['usage'].get('unsuccessful_transport_attempts',0)} unsuccessful transports. Attempt and recovery records are retained.",'',
        'Recovery restores already returned judgments only for identical original events and inputs. Publishing permission grants formal-guidance rights. Multi-organization and environment-dependent performance learning are later extensions.','',
        '[Results and audit](results.json) · [World summaries](world_summary.csv) · [Period trajectories](trajectories.csv) · [Methods and commands](../README.md)','',
        '## Independent replay without API calls','',
        'Four compressed probability files and replay_manifest.json reconstruct organizations, local inputs, input hashes, metrics and final states without credentials or original run directories.','',
        '```bash','python tools/replay_organizational_conventions.py --evidence docs/organizational_conventions/results','```','']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='complete',summary=report['summary']['jev'],audit=report['audit'],usage=report['usage']),indent=2))


if __name__=='__main__':main()
