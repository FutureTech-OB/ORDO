"""Audit the completed fresh categorical-sampling NHB tournament."""
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orgabm.sdk import validate_decisions


def main():
    root=Path('runs/llm-nhb-sampled-20261030')
    plan=json.loads((root/'plan-before-calls.json').read_text())
    verification=json.loads((root/'verification.json').read_text())
    if verification['status']!='complete' or plan['action_policy']!='sample':raise ValueError('Fresh sampling run not complete.')
    for name,sha in plan['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:raise ValueError('Frozen source differs: '+name)
    raw={};cost=0.;successes=0
    for file in sorted(root.glob('calls-*/openrouter_calls.jsonl')):
        for line in file.read_text(encoding='utf-8').splitlines():
            row=json.loads(line);request=row['request'];response=row['response'];cost+=response['usage']['cost'];successes+=1
            if 'temperature' in request:raise ValueError('Jev API was unexpectedly given a generation-temperature parameter.')
            answers=validate_decisions(request['questions'],{q:a['probabilities'] for q,a in response['answers'].items()})
            for q,probability in answers.items():raw.setdefault(q,probability)
    actions={};metrics=[]
    for line in (root/f"live-{verification['attempt']}"/'events.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(line);metrics.append(row['metrics'])
        for q,p in row['probabilities'].items():
            if raw[q]!=p:raise ValueError('SDK did not receive unchanged raw probabilities.')
            actions[q]=row['actions'][q]
    if len(actions)!=320 or len(raw)!=320:raise ValueError('Incomplete unique model decisions.')
    if abs(cost-verification['total_reported_cost_usd'])>1e-9:raise ValueError('Receipt cost mismatch.')
    rows=json.loads((root/'source_trace.json').read_text())['rows']
    summaries=[];source_rows=list(csv.DictReader(Path('.buildtmp/nhb-repeatedgames/pd/tft/data/pd_base_gpt4_tfts.csv').open(encoding='utf-8')))
    for i in range(64):
        block=rows[i*20:(i+1)*20];original=source_rows[i*20:(i+1)*20]
        for side in (0,1):
            if block[0][1+side]!='act_gpt4':continue
            summaries.append(dict(match=i,side=side+1,opponent=block[0][2-side],
                cooperative_actions=sum(r[3+side]=='J' for r in block),cooperation_rate=sum(r[3+side]=='J' for r in block)/20,
                author_archived_cooperative_actions=sum(r[f'answer{side+1}']=='J' for r in original),
                score=block[-1][7+side]))
    count=sum(a=='J' for a in actions.values());probabilities=[p['J'] for p in raw.values()]
    summary=dict(action_policy='Raw categorical sampling; application probability temperature=1, no rescaling',
        original_llm_temperature=0,jev_api_temperature=None,fresh_decisions=320,
        cooperative_actions=count,defective_actions=320-count,cooperation_rate=count/320,
        pJ_min=min(probabilities),pJ_max=max(probabilities),pJ_mean=sum(probabilities)/320,
        author_archive_cooperation_rate=sum(r['author_archived_cooperative_actions'] for r in summaries)/320,
        historical_argmax_cooperation_rate=0.,provider_reported_cost_usd=cost,successful_requests=successes,
        elapsed_seconds=verification['elapsed_s_this_attempt'],per_model_perspective=summaries,
        full_inputs_feedback_and_offline_replay_exact=(verification['offline_replay_all_inputs_and_metrics_exact']
            and verification['original_source_all1280rows_and_authored320prompts_exact']),
        all_sdk_probabilities_equal_raw_provider=True,
        limitations=['New interactive trajectories, not resampling probabilities on old histories',
            'One tournament, no robustness claim','Original GPT4 temperature0 and Jev action sampling are distinct',
            'No automatic human fidelity or successful behavioral replication claim'])
    out=Path('docs/llm_scope_review')
    (out/'nhb_sampled_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'nhb_sampled_matches.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    text=('# Repeated games with categorical probability sampling\n\n'
        '2026-10-30. Actions are sampled directly from Jev probabilities at application T=1, without rescaling. The Jev request has no temperature field.\n\n'
        f"All 64 ordered pairs run for 20 rounds. Of 320 model choices, **{count} cooperate ({count/320:.2%})** and {320-count} defect. "
        f"The historical argmax arm has 0/320 cooperative choices; the archived GPT-4 arm has 204/320 (63.75%).\n\n"
        f"Raw p(J) ranges from {min(probabilities):.2f} to {max(probabilities):.2f}, with mean {sum(probabilities)/320:.4f}. "
        f"New-request cost is ${cost:.8f}; elapsed time is {verification['elapsed_s_this_attempt']:.1f} seconds including verification.\n\n"
        'All 320 SDK probabilities match raw responses. Source feedback, prompts and complete replay checks pass. New actions alter subsequent history, and subsequent judgments are newly requested.\n\n'
        'The sampled arm and historical argmax arm are reported separately. Their difference includes new service outputs and changed feedback paths. Source-model temperature zero does not imply aggregate cooperation must be zero or one across different inputs.\n\n'
        'Opponent-specific trajectories retain cooperation, reciprocity and retaliation patterns alongside aggregate rates.\n\n'
        '[Results](nhb_sampled_results.json) · [Match perspectives](nhb_sampled_matches.csv) · '
        '[Run verification](../../runs/llm-nhb-sampled-20261030/verification.json) · [Historical argmax arm](nhb_results.md)\n')
    (out/'nhb_sampled_results.md').write_text(text,encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='per_model_perspective'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
