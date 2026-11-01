"""Organizational social-learning ABM with an explicit policy extension.

Based on the NK environment and synchronous learning in Barkoczi & Galesic
(2016). This is a Python reimplementation and policy extension, not an exact
reproduction of their R RNG or all published conditions.
"""
import collections
import json
import random
import numpy as np
from .randomness import stable_seed, sample

LENGTH=15
COMPLEXITY=7
POLICIES=[{'id':f'g{g}_p{p}','guidance':bool(g),'penalty':p} for g in (0,1) for p in (0,10)]

def landscape(seed,length=LENGTH,complexity=COMPLEXITY):
    rng=np.random.default_rng(stable_seed('landscape',seed,length,complexity))
    solutions=np.arange(2**length,dtype=np.int64)
    shifts=np.arange(length-1,-1,-1)
    bits=(solutions[:,None]>>shifts)&1
    raw=np.zeros(len(solutions))
    for i in range(length):
        # Match the author code's sampling from all dimensions (self may recur).
        deps=[i]+list(rng.choice(length,complexity,replace=False))
        table=np.round(rng.uniform(size=2**len(deps)),1)
        index=bits[:,deps]@(2**np.arange(len(deps)-1,-1,-1))
        raw+=table[index]/length
    return 100*(raw/raw.max())**8

def initialize(n,seed,policy,engine='jev'):
    rng=random.Random(stable_seed('initial',seed,n))
    return {'id':f'{engine}_s{seed}_{policy["id"]}','engine':engine,'seed':seed,
            'n':n,'policy':policy,'round':0,'positions':rng.sample(range(2**LENGTH),n),
            'balances':[0.0]*n,'histories':[[] for _ in range(n)],'metrics':[]}

def neighbors(n,seed,round_no,agent,size=3):
    # Implicit complete graph: no quadratic adjacency storage.
    selected=random.Random(stable_seed('contacts',seed,n,round_no,agent)).sample(range(n-1),size)
    return [x+(x>=agent) for x in selected]

def proposal(seed,round_no,agent,position):
    bit=random.Random(stable_seed('mutation',seed,round_no,agent)).randrange(LENGTH)
    return position^(1<<bit)

def rule_actions(world,scores,round_no,kind):
    actions=[];pos=world['positions']
    for agent in range(world['n']):
        peers=neighbors(world['n'],world['seed'],round_no,agent)
        rng=random.Random(stable_seed('rule_tie',world['seed'],round_no,agent))
        if kind=='best':
            best=max(scores[pos[j]] for j in peers)
            indices=[k for k,j in enumerate(peers) if scores[pos[j]]==best]
            k=rng.choice(indices)
        elif kind=='conformity':
            counts=collections.Counter(pos[j] for j in peers)
            if len(set(counts.values()))==1 and len(counts)>1:
                actions.append('explore');continue
            max_count=max(counts.values());chosen=rng.choice(sorted(s for s,c in counts.items() if c==max_count))
            k=next(k for k,j in enumerate(peers) if pos[j]==chosen)
        else:raise ValueError(kind)
        actions.append(f'copy_{k}' if scores[pos[peers[k]]]>scores[pos[agent]] else 'explore')
    return actions

def apply_actions(world,scores,round_no,actions,probabilities=None,peers_by_agent=None):
    assert round_no==world['round']+1 and len(actions)==world['n']
    old=list(world['positions']);new=list(old);charges=[];failures=0;successes=0;copies=0
    for a,action in enumerate(actions):
        charge=0.0;before=float(scores[old[a]])
        if action=='explore':
            candidate=proposal(world['seed'],round_no,a,old[a])
            success=bool(scores[candidate]>before)
            if success:new[a]=candidate;successes+=1
            else:charge=float(world['policy']['penalty']);failures+=1
        elif action.startswith('copy_'):
            index=int(action[-1]);assert 0<=index<3
            peer=(peers_by_agent[a] if peers_by_agent is not None else neighbors(world['n'],world['seed'],round_no,a))[index]
            if scores[old[peer]]>before:new[a]=old[peer];copies+=1
        elif action!='keep':raise ValueError(action)
        performance=float(scores[new[a]])
        net=performance-charge
        world['balances'][a]+=net
        # Visible private feedback, no untested alternative or global optimum.
        history={'t':round_no,'action':action,'gain':round(performance-before,3),
                 'failure_charge':charge,'net':round(net,3)}
        world['histories'][a]=(world['histories'][a]+[history])[-3:]
        charges.append(charge)
    world['positions']=new;world['round']=round_no
    counts=collections.Counter(new);freq=np.array(list(counts.values()))/world['n']
    attempts=actions.count('explore')
    metric={'round':round_no,'gross_performance':float(np.mean(scores[new])),
        'net_flow':float(np.mean(scores[new])-np.mean(charges)),
        'cumulative_net':float(np.mean(world['balances'])),
        'explore_share':attempts/world['n'],'successful_searches':successes,'failed_searches':failures,
        'adopted_copies':copies,'unique_solutions':len(counts),'solution_entropy':float(-(freq*np.log(freq)).sum()),
        'mean_failure_charge':float(np.mean(charges)),'actions':dict(collections.Counter(actions))}
    if probabilities is not None:
        metric['expected_explore_share']=float(np.mean([p.get('explore',0)/sum(p.values()) for p in probabilities]))
    world['metrics'].append(metric)
    return metric

def shared_state(rounds):
    return f'''Predict the action of an employee in an organizational learning simulation, with {rounds} decision rounds.
Each employee uses a 15-bit work process. A fixed unknown rugged task environment assigns each process a performance between 0 and 100 points per round. The employee observes their own process and the current processes and performance of three sampled coworkers. Processes interact through copying; the whole population updates simultaneously after all decisions.
Actions: keep the current process; copy one sampled coworker's process; or run one experiment changing one uniformly random bit. An experiment's outcome is unknown until it is run. The simulator retains a copied or experimental process only if it strictly improves performance, otherwise the old process remains. A non-improving experiment is a failed experiment and incurs the stated penalty. Copying and keeping have no failure charge. Round earnings equal resulting process performance minus the failure charge; earnings accumulate across rounds. No debt constraint prevents an action.
Management guidance is advisory; it does not mandate an exploration rate or change the stated payoffs. Employees seek to improve accumulated earnings over the remaining rounds and can respond to management guidance and their observed experience. Use only the employee information in each record. Each question is a separate employee decision. Return conditional action probabilities, not an explanation.'''

def choice_question(world,scores,round_no,agent,rounds):
    pos=world['positions'];peers=neighbors(world['n'],world['seed'],round_no,agent)
    labels={p:format(p,'015b') for p in [pos[agent]]+[pos[j] for j in peers]}
    policy=world['policy']
    guidance=('Management says: "Try new work processes and learn from experiments; exploration is encouraged."'
              if policy['guidance'] else 'Management has issued no guidance favoring exploration or copying.')
    records=[f'{k}: process={labels[pos[j]]}, performance={scores[pos[j]]:.3f}' for k,j in enumerate(peers)]
    prompt=(f'Round {round_no}/{rounds}. {guidance}\nPenalty for each failed experiment: {policy["penalty"]} points.\n'
            f'Your process={labels[pos[agent]]}, performance={scores[pos[agent]]:.3f}; accumulated earnings={world["balances"][agent]:.3f}.\n'
            'Coworkers:\n'+'\n'.join(records)+'\nRecent private outcomes: '+json.dumps(world['histories'][agent],separators=(',',':'))+
            '\nWhich action does this employee take now?')
    criteria={'keep':'Keep your current process.','explore':'Experiment with one random bit; its payoff is not yet known.',
              **{f'copy_{k}':f'Copy coworker {k}.' for k in range(3)}}
    order=list(criteria);random.Random(stable_seed('option_order',world['seed'],round_no,agent)).shuffle(order)
    return {'type':'choice','instructions':prompt,'criteria':{k:criteria[k] for k in order}}

def sample_actions(world,round_no,probabilities):
    return [sample(p,stable_seed('action',world['seed'],round_no,a)) for a,p in enumerate(probabilities)]

