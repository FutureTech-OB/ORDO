"""Public archived LLM-ABM replay and offline decision-interface verification.

python -m examples.llm_abm_cookbook.run --download --output runs/llm-abm-replay
No live decision API is called. Downloads are limited to pinned public data.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import platform
from statistics import mean, median

from orgabm.sdk import run_simulation
from .environments import NamingGame, ArchivedNamingEngine, digest
from .sources import ARCHIVES, load_sources
from .verify_interfaces import verify_interfaces


def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def replay_naming(source_run,output,options):
    world=NamingGame(source_run=source_run,options=options)
    run=run_simulation(world,ArchivedNamingEngine(source_run),
        rounds=len(source_run['tracker']['players']),seed=7,output=output)
    expected=[dict(players=p,answers=a,outcome=o) for p,a,o in zip(
        source_run['tracker']['players'],source_run['tracker']['answers'],source_run['tracker']['outcome'])]
    if world.events!=expected: raise AssertionError('Replayed interaction tracker differs from source.')
    if world.agents!=source_run['simulation']: raise AssertionError('Final individual histories/scores differ from source.')
    last=world.events[-3*world.n:]
    final_counts=Counter(a for e in last for a in e['answers'])
    return dict(interactions=run['completed_rounds'],decisions=run['decisions'],
        population_rounds=run['completed_rounds']/world.n,agents=world.n,
        source_tracker_exact=True,source_final_individual_state_exact=True,
        tracker_sha256=digest(world.events),final_state_sha256=digest(world.agents),
        initial_state_sha256=world.initial_sha256,
        committed_agents=sum(bool(a.get('committed_tag')) for a in world.agents.values()),
        recent_3N_success=mean(e['outcome'] for e in last),
        recent_3N_action_counts=dict(final_counts),
        archived_convergence=source_run.get('convergence'),
        source_action_semantics='sampled choices; original probabilities and option order unavailable',
        actual_model_api_calls=0)


def naming_report(sources,output):
    rows=[]
    for label,archive in sources['norms'].items():
        if label=='individual_W10': continue
        for run_id,episode in archive.items():
            if type(run_id) is not int: continue
            row=replay_naming(episode,output/f'{label}-{run_id}',
                              list('QMXYFJPRCD') if label=='spontaneous_W10' else ['Q','M'])
            row.update(condition=label,source_run=run_id,archive_member=ARCHIVES[label]); rows.append(row)
    individual=Counter(sources['norms']['individual_W10']['tracker']['answers'])
    by_condition={}
    for label in sorted({r['condition'] for r in rows}):
        subset=[r for r in rows if r['condition']==label]
        by_condition[label]=dict(episodes=len(subset),interactions=sum(r['interactions'] for r in subset),
            decisions=sum(r['decisions'] for r in subset),
            median_population_rounds=median(r['population_rounds'] for r in subset),
            final_3N_success_mean=mean(r['recent_3N_success'] for r in subset),
            final_3N_target_M_share_mean=mean(r['recent_3N_action_counts'].get('M',0)/sum(r['recent_3N_action_counts'].values()) for r in subset))
    report=dict(evidence='archived_author_LLM_action_replay',source_model_subset='Claude archive only',
        episodes=len(rows),interactions=sum(r['interactions'] for r in rows),
        decisions=sum(r['decisions'] for r in rows),all_trackers_exact=True,all_final_individual_states_exact=True,
        conditions=by_condition,individual_no_memory_choices=dict(individual),
        individual_no_memory_n=sum(individual.values()),runs=rows)
    write_json(output/'verification.json',report)
    return report


def opinion_report(sources,output):
    output.mkdir(); traces=[]; table_rows=[]
    for filename,segments in sources['curves'].items():
        for index,segment in enumerate(segments):
            name=f'{filename.removesuffix(".txt")}-segment-{index}.csv'
            with (output/name).open('w',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream); writer.writerow(['recorded_step','population_time','magnetization','coordination','positive_count','negative_count'])
                for t,m in segment:
                    positive=round((m+1)*50/2)
                    writer.writerow([t,t/50,m,abs(m),positive,50-positive])
            first_consensus=next((t for t,m in segment if abs(m)>=1-1e-9),None)
            traces.append(dict(source_file=filename,segment=index,rows=len(segment),first_recorded_step=segment[0][0],
                segment_origin='zero-origin record' if segment[0][0]==0 else 'nonzero overlapping fragment; not an independent trial',
                last_recorded_step=segment[-1][0],first_consensus_recorded_step=first_consensus,
                consensus_observed=first_consensus is not None,
                interpretation='consensus observed' if first_consensus is not None else 'right-censored in this recorded segment',
                final_coordination=abs(segment[-1][1]),output_csv=name))
    for filename,rows in sources['tables'].items():
        differences=[]
        for index,row in enumerate(rows):
            if len(row)==4:
                _,k,z,p=row
                if abs(k/(k+z)-p)>1e-7:
                    differences.append(dict(row=index,k=k,z=z,reported_share=p,share_among_recorded_choices=k/(k+z)))
        table_rows.append(dict(source_file=filename,rows=len(rows),columns=len(rows[0]),
                               reported_share_count_discrepancies=differences))
    # These published probabilities are reference evidence only, never an engine.
    write_json(output/'adoption_reference_tables.json',sources['tables'])
    report=dict(evidence='macro_trajectory_import_and_integrity_checks_only',population=50,
        curve_files=len(sources['curves']),segments=len(traces),recorded_rows=sum(t['rows'] for t in traces),
        zero_origin_segments=sum(t['first_recorded_step']==0 for t in traces),
        nonzero_overlapping_fragments=sum(t['first_recorded_step']!=0 for t in traces),
        segments_with_observed_consensus=sum(t['consensus_observed'] for t in traces),
        zero_origin_segments_with_observed_consensus=sum(t['consensus_observed'] and t['first_recorded_step']==0 for t in traces),
        adoption_tables=len(table_rows),adoption_rows=sum(t['rows'] for t in table_rows),
        table_rows_with_count_share_discrepancy=sum(len(t['reported_share_count_discrepancies']) for t in table_rows),
        validation=['finite values','integer population counts','consecutive steps within each segment','single-agent step bound'],
        micro_action_replay=False,probability_reuse=False,traces=traces,tables=table_rows)
    write_json(output/'verification.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',default='.buildtmp/llm-abm-sources')
    parser.add_argument('--download',action='store_true',help='Fetch missing hash-pinned public research data only.')
    parser.add_argument('--output',required=True,help='A new output directory.')
    args=parser.parse_args()
    root=Path(args.output); root.mkdir(parents=True,exist_ok=False)
    manifest=dict(status='running',python=platform.python_version(),actual_model_api_calls=0,
        requested_scope='archived replay and mocked interfaces',probability_reuse=False,
        source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})
    try:
        sources=load_sources(args.sources,args.download)
        write_json(root/'source_manifest.json',sources['sources'])
        naming=root/'naming'; naming.mkdir()
        manifest['naming']=naming_report(sources,naming)
        manifest['opinion']=opinion_report(sources,root/'opinion')
        manifest['interfaces']=verify_interfaces(root/'interfaces')
        manifest['status']='complete'
    except Exception as error:
        manifest.update(status='failed',error_type=type(error).__name__)
        raise
    finally: write_json(root/'verification.json',manifest)
    print(json.dumps(dict(status=manifest['status'],naming_episodes=manifest['naming']['episodes'],
        naming_interactions=manifest['naming']['interactions'],naming_decisions=manifest['naming']['decisions'],
        opinion_segments=manifest['opinion']['segments'],interface_cases=len(manifest['interfaces']['cases']),
        actual_model_api_calls=0),indent=2))


if __name__=='__main__': main()
