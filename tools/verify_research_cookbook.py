"""Check frozen cookbook evidence and units without rerunning simulations/APIs."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re


def main():
    repo=Path(__file__).resolve().parents[1]
    catalog=json.loads((repo/'examples/research_cookbook/catalog.json').read_text(encoding='utf-8'))
    studies={s['id'] for s in catalog['studies']}
    for entry in catalog['entries']:
        if not set(entry['study_ids'])<=studies:raise ValueError('Unknown source study ID.')
        for key in ['docs','evidence']:
            if not (repo/entry[key]).is_file():raise ValueError('Missing catalog target: '+entry[key])
        if not (repo/(entry['module'].replace('.','/')+'.py')).is_file():raise ValueError('Missing entry module.')
    files={
        'games':('docs/nc_evolutionary_games/results/verification.json','examples/nc_evolutionary_games'),
        'rewarding':('docs/nc_additional_games/results/verification.json','examples/nc_additional_games'),
        'cascades':('docs/nc_social_sweep/results/verification.json','examples/nc_social_sweep'),
        'foraging':('docs/nc_social_sweep/foraging_results/verification.json','examples/nc_social_sweep'),
        'mobility':('docs/ncs_mobility/results.json','examples/ncs_mobility'),
        'polarization':('docs/nc_polarization/results/verification.json','examples/nc_polarization')}
    reports={};hashes=0
    for key,(file,base) in files.items():
        r=json.loads((repo/file).read_text(encoding='utf-8'));reports[key]=r
        if r['status']!='complete':raise ValueError('Partial evidence: '+key)
        if r.get('actual_model_api_calls',r.get('actual_api_calls'))!=0:raise ValueError('Unexpected paid/model execution.')
        for name,sha in r['source_hashes'].items():
            p=Path(name)
            if p.is_absolute():p=repo/base/p.name
            elif len(p.parts)>1:p=repo/p
            else:p=repo/base/name
            if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('Frozen source mismatch: '+str(p))
            hashes+=1
        if 'analysis_sha256' in r:
            if hashlib.sha256((repo/base/'export.py').read_bytes()).hexdigest()!=r['analysis_sha256']:
                raise ValueError('Export source mismatch: '+key)
    g,reward,c,f,m,p=[reports[k] for k in ['games','rewarding','cascades','foraging','mobility','polarization']]
    assert g['comparisons']['pair_states_exact'] and g['comparisons']['pair_payoffs_exact'] and g['comparisons']['evolution_population_states_exact']
    assert reward['all_source_states_exact'] and reward['all_source_metrics_exact']
    assert all(w['exact_author_shell_sizes'] and w['all_inputs_and_states_replay_exact'] for w in c['worlds'])
    assert all(w['exact_author_step_statistics'] and w['exact_author_full_states'] and w['exact_local_observation_replay'] for w in f['worlds'])
    assert all(w['all_period_metrics_and_state_hashes_exact'] and w['full_final_state_exact'] for w in m['cases'])
    assert all(w['all_205_figure_counts_exact'] and w['all_states_and_edge_rows_exact'] for w in p['topics'].values())
    for entry in catalog['entries']:
        doc=repo/entry['docs']
        for target in re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            if not (doc.parent/target.split('#')[0]).exists():raise ValueError('Broken local link: '+str(doc)+' '+target)
    population_worlds=g['evolution_worlds']+len(reward['worlds'])+len(c['worlds'])+len(f['worlds'])+len(m['cases'])
    result=dict(status='complete',verified_utc=datetime.now(timezone.utc).isoformat(),catalog_entries=len(catalog['entries']),
        distinct_referenced_studies=len(studies),added_papers=6,added_author_kernel_or_loop_studies=5,added_archive_studies=1,
        added_pair_games=g['pair_worlds'],added_population_worlds=population_worlds,
        native_rule_choices=sum(r['decisions'] for r in [g,reward,c,f]),
        mobility_native_agent_updates=m['native_agent_updates'],mobility_sdk_period_control_actions=m['sdk_control_actions'],
        archived_snapshots=p['total_snapshots'],archived_state_assignments=p['total_restored_member_states'],
        archived_directed_edge_rows=p['total_directed_edge_rows'],actual_model_api_calls=0,
        adapter_source_hashes_checked=hashes,all_declared_reference_checks_passed=True,all_catalog_paths_and_links_valid=True,
        source_reports={k:v[0] for k,v in files.items()},
        units='Pair games, population worlds, native choices, native movement updates, period controls and restored archive states are distinct quantities.')
    out=repo/'docs/cookbook/coverage_verification.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
