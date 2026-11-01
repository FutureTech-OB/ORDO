"""Full original N=50 condition, all 20 independent replacement-model realizations."""
from .model import OriginalMajority


def build_cases():
    return [dict(id=f'demarzo-fig2-n50-r{i:02d}',paper_id='sa_demarzo_2026',seed=2026103000+i,
                 condition='Fig2_N50_m0zero_t10',environment=OriginalMajority(seed=2026103000+i),rounds=500)
            for i in range(20)]


def analyze(entries):
    rows=[]
    for e in entries:
        active=[m for m in e['result']['metrics'] if not m.get('padding')]
        final=active[-1]
        rows.append(dict(id=e['id'],seed=e['seed'],updates=final['update'],
            population_time=final['population_time'],final_coordination=final['coordination'],
            final_mean_opinion=final['mean_opinion'],positive_count=final['positive_count'],
            source_last_preupdate_coordination=abs(final['source_preupdate_mean_opinion']),
            reached_consensus=final['consensus'],first_consensus_update=final['first_consensus_update'],
            stop=final['stop'],decisions=e['result']['decisions']))
    return dict(scope='All 20 realizations of original Fig.2 N50/m0=0/t_max10 condition, adding Jev as a replacement-model arm; not all five original models or the full paper.',
        worlds=len(rows),cases=rows,consensus_worlds=sum(r['reached_consensus'] for r in rows),
        mean_final_coordination=sum(r['final_coordination'] for r in rows)/len(rows),
        raw_final_coordination=[r['final_coordination'] for r in rows],
        complete_original_condition=len(rows)==20 and all(r['stop'] in ('consensus','horizon') for r in rows),
        behavior_claim='Report actual outcomes against published-model distributions; successful interface execution is not a positive phenomenon-replication result.')
