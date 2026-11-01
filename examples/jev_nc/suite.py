"""Build fresh-decision NC worlds; the caller injects its real decision engine."""
from statistics import mean
from .environments import FreshRepeatedGame,FreshSocialRewarding,FreshForaging,foraging_modules


def build_cases():
    cases=[]
    for incident in ('CC','CD','DD'):
        for seed in (7,11):
            cases.append(dict(id=f'nc_pd_{incident}_s{seed}',paper_id='nc_repeated_games',
                environment=FreshRepeatedGame(initial=incident,pairs=4,rounds=12,seed=seed),
                rounds=12,seed=seed,condition=dict(initial=incident)))
    for information in (0,.5,1):
        for seed in (7,11):
            cases.append(dict(id=f'nc_reward_l{information}_s{seed}',paper_id='nc_social_rewarding',
                environment=FreshSocialRewarding(information=information,agents=16,rounds=6,seed=seed),
                rounds=6,seed=seed,condition=dict(information=information)))
    task,sim,cache=foraging_modules()
    for pattern in ('smooth','random'):
        for cues in (False,True):
            for seed in (7,11):
                cases.append(dict(id=f'nc_forage_{pattern}_cues{int(cues)}_s{seed}',paper_id='nc_collective_foraging',
                    environment=FreshForaging(task,sim,cache,environment=pattern,social_cues=cues,seed=seed,steps=120),
                    rounds=480,seed=seed,condition=dict(pattern=pattern,social_cues=cues)))
    return cases


def analyze(results):
    """Descriptive direction tests only; never assume Jev matches a paper."""
    output=dict(scope='Fresh behavioral substitution on paper-derived worlds; not original exact trajectories, fitted human data, or full-paper replication.',
        inference='Two seeds per condition; exploratory directional checks, no significance or general fidelity claim.',papers={})
    for paper in ('nc_repeated_games','nc_social_rewarding','nc_collective_foraging'):
        rows=[]
        for case in results:
            if case['paper_id']!=paper:continue
            result=case['result'];metrics=result['metrics']
            row=dict(id=case['id'],seed=case['seed'],condition=case['condition'],
                status=result['status'],decisions=result['decisions'])
            if not metrics:continue
            if paper=='nc_repeated_games':
                row.update(early_cooperation=mean(x['cooperation'] for x in metrics[:3]),
                    late_cooperation=mean(x['cooperation'] for x in metrics[-3:]),
                    late_mutual_cooperation=mean(x['mutual_cooperation'] for x in metrics[-3:]),
                    final_mean_points=metrics[-1]['mean_cumulative_payoff'])
            elif paper=='nc_social_rewarding':
                row.update(late_cooperation=mean(x['cooperation'] for x in metrics[-2:]),
                    late_social_rewarding=mean(x['social_rewarding_share'] for x in metrics[-2:]),
                    final_strategy_counts=metrics[-1]['strategy_counts'])
            else:
                last=metrics[-1];row.update(physical_complete=last.get('complete',False),
                    rewards=last.get('cumulative_reward'),revealed=last.get('revealed'),goal_decisions=last.get('goal_decisions'))
            rows.append(row)
        if not rows:
            output['papers'][paper]=dict(status='no_results');continue
        if paper=='nc_repeated_games':
            groups={c:mean(r['late_mutual_cooperation'] for r in rows if r['condition']['initial']==c)
                for c in ('CC','CD','DD') if any(r['condition']['initial']==c for r in rows)}
            output['papers'][paper]=dict(worlds=rows,late_mutual_cooperation_by_incident=groups,
                paper_expectation='The learned reciprocal strategy can sustain cooperation and resolve initial conflict; this rerun tests fresh Jev instead of that trained strategy.',
                supports_exploratory_recovery_pattern=(all(groups.get(c,0)>.5 for c in ('CC','CD','DD')) if len(groups)==3 else None),
                threshold='Exploratory majority of pairs mutually cooperating over final three rounds in all initial-incident conditions; not a paper effect-size estimate.')
        elif paper=='nc_social_rewarding':
            groups={str(l):dict(cooperation=mean(r['late_cooperation'] for r in rows if r['condition']['information']==l),
                social_rewarding=mean(r['late_social_rewarding'] for r in rows if r['condition']['information']==l))
                for l in (0,.5,1) if any(r['condition']['information']==l for r in rows)}
            # str(0) and str(1) are stable even when condition values are floats.
            low=groups.get('0');high=groups.get('1')
            coop=None if low is None or high is None else high['cooperation']-low['cooperation']
            reward=None if low is None or high is None else high['social_rewarding']-low['social_rewarding']
            output['papers'][paper]=dict(worlds=rows,late_means_by_information=groups,
                paper_expectation='Greater transmissibility of reward reputations promotes cooperation and social rewarding in the original evolutionary setting.',
                cooperation_high_minus_low=coop,social_rewarding_high_minus_low=reward,
                supports_both_directional_predictions=None if coop is None else bool(coop>0 and reward>0))
        else:
            means={}
            for pattern in ('smooth','random'):
                for cues in (False,True):
                    selected=[r for r in rows if r['condition']==dict(pattern=pattern,social_cues=cues) and r['physical_complete']]
                    if selected:means[f'{pattern}_cues{int(cues)}']=mean(r['rewards'] for r in selected)
            required=[f'{p}_cues{i}' for p in ('smooth','random') for i in (0,1)]
            interaction=None
            if all(k in means for k in required):interaction=(means['smooth_cues1']-means['smooth_cues0'])-(means['random_cues1']-means['random_cues0'])
            output['papers'][paper]=dict(worlds=rows,mean_group_rewards=means,
                paper_expectation='Social success cues are more useful for clustered smooth resources than random resources; original selective-policy superiority need not transfer to an untrained Jev policy.',
                cue_benefit_smooth_minus_random=interaction,supports_directional_interaction=None if interaction is None else interaction>0,
                boundary='Ablates explicit social cues only; observed revealed rewards remain, and 24-cell shortlist differs from original full-grid policy.')
    return output
