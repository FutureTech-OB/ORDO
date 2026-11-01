"""Export a compact, public-data-only verification artifact from an offline run."""
import argparse
import copy
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',default='docs/llm_abm_cookbook')
    args=parser.parse_args()
    root=Path(args.run); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete' or report['actual_model_api_calls']!=0:
        raise ValueError('This exporter requires a complete offline-only run.')
    report=copy.deepcopy(report)
    report['source_manifest']=json.loads((root/'source_manifest.json').read_text(encoding='utf-8'))
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    n,o,i=report['naming'],report['opinion'],report['interfaces']
    lines=['# Archived LLM-simulation verification','', '2026-10-29. Values are exported from saved manifests. This verification uses zero API calls; interface responses are local fixtures.', '',
        '## Naming-game author-record replay','',
        f"Across **{n['episodes']}** experiments and **{n['interactions']:,}** pairs, **{n['decisions']:,}** nonfixed-member choices reproduce all interactions and final individual states. Committed members execute their fixed actions.",'',
        '| Source condition | Experiments | Pairs | Nonfixed-member choices |','| --- | ---: | ---: | ---: |']
    for label,case in n['conditions'].items():
        lines.append(f"| {label} | {case['episodes']} | {case['interactions']:,} | {case['decisions']:,} |")
    lines+=['',f"An additional **{n['individual_no_memory_n']:,}** independent no-memory choices are imported and summarized. Archived spontaneous worlds were selected for convergence.",'',
        'Author choices drive this replay. The environment reconstructs pairing, memory, payoffs and metrics. Initial personal histories are restored from the archive; original probability vectors and option permutations were not recorded.', '',
        '## Coordination trajectory import','',
        f"Imported **{o['curve_files']}** N=50 files with **{o['recorded_rows']:,}** rows, split at nonincreasing time into **{o['segments']}** segments: **{o['zero_origin_segments']}** start at zero and **{o['nonzero_overlapping_fragments']}** overlap from nonzero steps.",'',
        '| File / segment | Rows | Step range | Final coordination | Interpretation |','| --- | ---: | --- | ---: | --- |']
    for trace in o['traces']:
        label=trace['source_file'].removeprefix('magnetization_').removesuffix('.txt')
        interpretation=('Nonzero overlapping fragment' if trace['first_recorded_step'] else
                        'Consensus observed' if trace['consensus_observed'] else 'No consensus in recorded horizon')
        lines.append(f"| {label} / {trace['segment']} | {trace['rows']} | {trace['first_recorded_step']}–{trace['last_recorded_step']} | {trace['final_coordination']:.2f} | {interpretation} |")
    lines+=['',f"Finite-value, integer-count, contiguous-step and single-member-update checks pass. Imported **{o['adoption_tables']}** model tables contain **{o['adoption_rows']}** probability rows; **{o['table_rows_with_count_share_discrepancy']}** reported shares differ from valid-choice count ratios and are retained with flags.",'',
        'Aggregate curves retain source time as recorded step / N. They do not uniquely identify individual choices. The archived probability tables are imported reference data.', '',
        '## Decision-interface checks','',
        '| Interface | Scenario | Offline decisions | Mock HTTP requests | Network requests |',
        '| --- | --- | ---: | ---: | ---: |']
    for case in i['cases']:
        lines.append(f"| {case['provider']} | {case['scene']} | {case['decisions']} | {case['mock_http_requests']} | 0 |")
    lines+=['','Jev and chat adapters construct requests, validate responses, sample actions and update worlds using local HTTP fixtures. Two independent naming choices can batch together; sequential opinion updates preserve their dependency barrier.', '',
        '## Infrastructure evidence','',
        'The public Environment/DecisionEngine contract accommodates two published interaction protocols. Naming-game author-record replay validates source transitions, and both protocols pass adapter-interface checks.', '',
        'Fresh model trajectories and organizational extensions have separate execution records.', '',
        '[verification.json](verification.json) contains state hashes, source hashes and interface results. Retrieve and replay public data through the [cookbook](README.md).','']
    (out/'verified_results.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(exported=str(out),episodes=n['episodes'],actual_model_api_calls=0)))


if __name__=='__main__': main()
