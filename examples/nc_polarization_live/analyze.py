"""Independent comparison to author future trajectories, used only after inference."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

from examples.nc_polarization.archive import metrics


def analyze(run,*,evidence='docs/nc_polarization/results'):
    run=Path(run);evidence=Path(evidence)
    verification=json.loads((run/'verification.json').read_text(encoding='utf-8'))
    if verification['status']!='complete':raise ValueError('Do not analyze an incomplete world as a completed result.')
    replay_manifest=json.loads((evidence/'replay_manifest.json').read_text(encoding='utf-8'))
    payload=(evidence/replay_manifest['file']).read_bytes()
    if hashlib.sha256(payload).hexdigest()!=replay_manifest['sha256']:raise ValueError('Reference archive changed.')
    author=json.loads(gzip.decompress(payload))['Gun Control']
    reference=[dict(epoch=t,**metrics(s)) for t,s in enumerate(author)]
    actual=json.loads((run/'trajectory.json').read_text(encoding='utf-8'))
    if [r['epoch'] for r in actual]!=list(range(41)):raise ValueError('A complete 0..40 trajectory is required.')
    fields=['neutral_share','polarization','mean_opinion','exact_opinion_homophily','same_sign_homophily']
    # The hybrid epoch 0 includes new seed-person updates; the unmodified source epoch 0 is separately disclosed.
    rows=[dict(epoch=t,**{f'{name}_{field}':r[field] for name,r in [('author',reference[t]),('hybrid',actual[t])] for field in fields}) for t in range(41)]
    with (run/'comparison.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    plan=json.loads((run/'plan-before-calls.json').read_text(encoding='utf-8'));initial=plan['initial_metrics']
    changes={name:dict(neutral_change=seq[-1]['neutral_share']-initial['neutral_share'],
                       mean_absolute_opinion_change=seq[-1]['polarization']-initial['polarization'])
             for name,seq in [('author',reference),('hybrid',actual)]}
    final=actual[-1];ref=reference[-1]
    summary=dict(study_doi=plan['study_doi'],population=1000,epochs=40,independent_worlds=1,
        models=dict(decision=plan['jev_model'],content=plan['content_model'],reasoning=plan['content_reasoning']),
        initial_author_metrics=initial,post_seed_hybrid_epoch0=actual[0],author_final=ref,hybrid_final=final,
        changes_from_shared_preseed_initial=changes,
        same_direction_neutral_and_polarization=(changes['hybrid']['neutral_change']<0 and changes['hybrid']['mean_absolute_opinion_change']>0),
        trajectory_rmse={field:math.sqrt(sum((a[field]-b[field])**2 for a,b in zip(actual,reference))/41) for field in fields},
        final_opinion_distribution_total_variation=.5*sum(abs(final['counts'][str(s)]-ref['counts'][str(s)])/1000 for s in range(-2,3)),
        actual_cost_usd=sum(verification['total_usage'][k] for k in ('jev_cost','content_cost')),
        uncertain_reserved_cost_usd=sum(verification['total_usage'][k] for k in ('jev_reserve','content_reserve')),
        costs_separated=verification['total_usage'],fresh_counts=verification['cumulative_counts'],
        full_input_content_action_state_replay_exact=verification['offline_all_inputs_text_actions_and_final_state_exact'],
        scope='One hybrid replacement arm; direction agreement is not numerical equivalence, statistical replication, improved human fidelity, or a pure Jev speed/cost benchmark.')
    (run/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,3,figsize=(13,3.5))
        for ax,field,label in zip(axes,('neutral_share','polarization','same_sign_homophily'),('Neutral share','Mean absolute opinion','Same-sign edge share')):
            ax.plot(range(41),[r[field] for r in reference],label='Author archive',color='#666666')
            ax.plot(range(41),[r[field] for r in actual],label='Fresh Jev + DeepSeek',color='#2563eb')
            ax.set(xlabel='Epoch',ylabel=label);ax.legend(fontsize=8);ax.grid(alpha=.15)
        fig.suptitle('Gun Control: one 1,000-person / 40-epoch hybrid arm');fig.tight_layout()
        fig.savefig(run/'comparison.png',dpi=180);plt.close(fig)
    except ImportError:pass
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    print(json.dumps(analyze(p.parse_args().run),ensure_ascii=False,indent=2))
