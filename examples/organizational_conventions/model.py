"""Organizational positions, reporting channels and permission-filtered guidance.

This is an explicit extension: disjoint pairs act synchronously within a period.
MemoryForest and workforce APIs remain the shared ORDO components.
"""
from collections import Counter,deque
import copy
import json
import random

from orgabm.memory import MemoryForest
from orgabm.personas import digest,private_persona,validate_population
from orgabm.randomness import stable_seed
from orgabm.sdk import DecisionBatch
from orgabm.workforce import build_workforce,validate_structure


STATE=("Independent questions concern members of one organization coordinating on convention Q or M. "
       "Each listed pair chooses simultaneously: equal choices give both +100 points; unequal choices give both -50. "
       "Predict the focal member's voluntary choice from this record only. History rows are [own choice,partner choice,payoff]; "
       "local_points sums the displayed history. Role and relationship describe the actual reporting structure. "
       "Bulletins are permission-filtered department messages. A peer note is a member's informal suggestion. "
       "An official guidance record was issued under a simulator-validated delegated publishing right; it is still advisory: "
       "neither action is prohibited, and ignoring guidance has no extra financial penalty. "
       "Do not assume that a manager is automatically correct. Only the supplied history and bulletins are known; "
       "other members' private histories and current choices are unavailable. Persona describes the person, separately from their job. "
       "Return fresh choice probabilities for each question, without access to other questions' answers.")


def organization_config(agents,departments,seed,population=None):
    if type(agents) is not int or not 40<=agents<=10000 or type(departments) is not int or departments<2 or agents%departments or agents//departments<4:
        raise ValueError('Use 40..10,000 members in equal departments of at least four.')
    size=agents//departments
    roles={r:dict(title=t,responsibilities=d,allowed_actions=['Q','M']) for r,t,d in [
        ('employee','Department employee','Coordinate work within assigned responsibilities.'),
        ('manager','Department manager','Coordinate the department and report to the executive.'),
        ('executive','Organization executive','Coordinate departments through their managers.')]}
    assignments=[dict(agent=a,department=a//size,
        role='executive' if a==0 else 'manager' if a%size==0 else 'employee',
        manager=None if a==0 else 0 if a%size==0 else (a//size)*size) for a in range(agents)]
    structure=validate_structure(dict(template='custom',roles=roles,assignments=assignments),agents,departments,
                                 capabilities=['Q','M'],required_action='Q')
    if population is None:
        population=dict(records=[dict(id='neutral-fictional-profile',description='Fictional member with experience in routine coordination.',
            source={'kind':'synthetic_controlled_fixture'})],sampling='with_replacement',seed=seed)
    return dict(agents=agents,departments=departments,seed=seed,structure=structure,
                population=validate_population(population,agents))


class OrganizationalConventions:
    def __init__(self,*,agents=1000,departments=50,committed=20,placement='employee',message_mode='none',
                 seed=7,rounds=32,pairs_per_round=None,hierarchy_bias=.6,cross_probability=.1,
                 release_round=1,organization_id='org-1',population=None):
        if placement not in ('employee','manager') or message_mode not in ('none','peer','official'):
            raise ValueError('Choose employee/manager placement and none/peer/official messages.')
        if type(rounds) is not int or not 1<=rounds<=1000: raise ValueError('Use 1..1,000 organizational periods.')
        if type(committed) is not int or not 0<=committed<departments:
            raise ValueError('Place at most one seed per non-headquarters department.')
        if not 0<=hierarchy_bias<=1 or not 0<=cross_probability<=1 or hierarchy_bias+cross_probability>1:
            raise ValueError('Reporting and cross-department probabilities must be nonnegative and sum to <=1.')
        if type(release_round) is not int or not 1<=release_round<=rounds: raise ValueError('Invalid disclosure period.')
        config=organization_config(agents,departments,seed,population)
        self.roster=build_workforce(config,[a//(agents//departments) for a in range(agents)])
        self.n=agents; self.departments=departments; self.size=agents//departments
        self.seed=seed; self.rounds=rounds; self.placement=placement; self.message_mode=message_mode
        self.organization_id=organization_id; self.hierarchy_bias=hierarchy_bias; self.cross_probability=cross_probability
        self.release_round=release_round; self.pair_budget=agents//8 if pairs_per_round is None else pairs_per_round
        if type(self.pair_budget) is not int or not 1<=self.pair_budget<=agents//2: raise ValueError('Invalid disjoint-pair budget.')
        self.members={d:list(range(d*self.size,(d+1)*self.size)) for d in range(departments)}
        self.seed_departments=sorted(random.Random(stable_seed('seed-departments',seed)).sample(range(1,departments),committed))
        self.seed_ids=set()
        for d in self.seed_departments:
            self.seed_ids.add(d*self.size if placement=='manager' else random.Random(stable_seed('seed-worker',seed,d)).choice(self.members[d][1:]))
        self.publication_grants={a:self.roster[a]['department'] for a in self.seed_ids} if message_mode=='official' else {}
        self.memory=self._memory()
        self.history=[deque([['Q','Q',100] for _ in range(5)],maxlen=5) for _ in range(agents)]
        self.scores=[500]*agents; self.last=['M' if a in self.seed_ids else 'Q' for a in range(agents)]
        self.encounters=[0]*agents; self.bulletin_exposures=[0]*agents
        self.seed_contact_count=0; self.pair_count=0; self.round=0; self.pending=None; self.last_audits={}
        self._order=list(range(agents)); random.Random(stable_seed('initiator-order',seed,0)).shuffle(self._order)
        self._cursor=0; self._cycle=0
        self.population_sha256=digest([r['persona'] for r in self.roster])
        self.structure_sha256=digest(config['structure'])
        self.config=dict(agents=agents,departments=departments,committed=committed,placement=placement,
            message_mode=message_mode,seed=seed,rounds=rounds,pairs_per_round=self.pair_budget,
            hierarchy_bias=hierarchy_bias,cross_probability=cross_probability,release_round=release_round,
            organization_id=organization_id)

    def publication_record(self,writer,department,value='M',*,official=False):
        if type(writer) is not int or not 0<=writer<self.n or self.roster[writer]['department']!=department:
            raise PermissionError('A member may only submit a note to their own department.')
        if value not in ('Q','M'): raise ValueError('Unknown convention.')
        if official and self.publication_grants.get(writer)!=department:
            raise PermissionError('No delegated right to publish official guidance for this department.')
        return dict(value=value,issuer=writer,issuer_role=self.roster[writer]['role'],
                    channel='official' if official else 'peer')

    def _memory(self):
        trees=[]
        if self.message_mode!='none':
            for a in sorted(self.seed_ids):
                d=self.roster[a]['department']
                record=self.publication_record(a,d,official=self.message_mode=='official')
                trees.append(dict(id=f'department-{d}',scope='department',owner=d,
                    nodes=[dict(id='coordination-note',title='Department coordination notice',
                        summary='A member recommends convention M.',content=json.dumps(record,separators=(',',':')),
                        grants=[dict(audience=[{'everyone':True}],level='detail',from_round=self.release_round)])]))
        return MemoryForest(dict(organization_id=self.organization_id,max_items=2,max_chars=2000,trees=trees),self.roster)

    def describe(self):
        return dict(scenario='organizational_conventions',**self.config,source_doi='10.1126/sciadv.adu9368',
            protocol='organizational-extension-v1',population_sha256=self.population_sha256,
            structure_sha256=self.structure_sha256,memory_policy_sha256=self.memory.policy_hash,
            seed_departments=self.seed_departments,seed_ids=sorted(self.seed_ids),
            layers='executive -> department managers -> employees; headquarters employees report to executive',
            authority_scope='validated official-guidance publication right, not mandatory action compliance',
            scheduling='disjoint pairs within a period; all choices before all updates; changed from original asynchronous protocol',
            future_boundary='organization_id supports information isolation; no interorganization interaction in this scene')

    def _initiator(self):
        if self._cursor==self.n:
            self._cycle+=1; self._cursor=0
            random.Random(stable_seed('initiator-order',self.seed,self._cycle)).shuffle(self._order)
        a=self._order[self._cursor]; self._cursor+=1
        return a

    def _pairs(self,t):
        rng=random.Random(stable_seed('org-pairs',self.seed,t)); used=set(); pairs=[]
        while len(pairs)<self.pair_budget:
            a=self._initiator()
            if a in used: continue
            own=self.roster[a]; u=rng.random(); candidates=[]; channel='department'
            if u<self.hierarchy_bias:
                candidates=[x for x in [own['manager'],*own['direct_reports']] if x is not None and x not in used]
                channel='reporting'
            elif u<self.hierarchy_bias+self.cross_probability:
                channel='cross_department'
                candidates=[x for x in rng.sample(range(self.n),min(self.n,40)) if x not in used and self.roster[x]['department']!=own['department']]
            if not candidates:
                channel='department'; candidates=[x for x in self.members[own['department']] if x!=a and x not in used]
            if not candidates:
                channel='fallback_cross'; candidates=[x for x in range(self.n) if x!=a and x not in used]
            b=rng.choice(candidates); pairs.append((a,b,channel)); used.update((a,b))
        return pairs

    def local_record(self,a,b,t):
        own,peer=self.roster[a],self.roster[b]
        view,audit=self.memory.observe(a,t,organization_id=self.organization_id)
        notes=[json.loads(x['content']) for x in view['items'] if x['level']=='detail']
        relation='manager' if own['manager']==b else 'direct_report' if peer['manager']==a else 'coworker'
        return dict(role=own['role'],department=own['department'],reports_to=own['manager'],
            partner_role=peer['role'],partner_department=peer['department'],partner_relation=relation,
            history=list(self.history[a]),local_points=sum(row[2] for row in self.history[a]),
            bulletins=notes,persona=private_persona(own['persona']) if own['persona'] else None),audit

    def prepare(self,t):
        if self.pending is not None or t!=self.round+1: raise ValueError('Finish the preceding organizational period.')
        pairs=self._pairs(t); questions={}; ids={}; self.last_audits={}
        for a,b,_ in pairs:
            for focal,partner in ((a,b),(b,a)):
                if focal in self.seed_ids: continue
                record,audit=self.local_record(focal,partner,t); self.last_audits[focal]=audit
                options=['Q','M']; random.Random(stable_seed('org-option-order',self.seed,t,focal)).shuffle(options)
                qid=f't{t}_a{focal}'
                questions[qid]=dict(type='choice',instructions=json.dumps(record,separators=(',',':'),ensure_ascii=False),
                    criteria={k:f'Choose {k}.' for k in options})
                ids[qid]=focal
        self.pending=(t,pairs)
        return DecisionBatch(STATE,questions,ids)

    def advance(self,t,actions,probabilities):
        if self.pending is None or self.pending[0]!=t: raise ValueError('Prepare this period first.')
        events=[]
        # Pairs are disjoint and every decision has already been sampled by the SDK.
        for a,b,channel in self.pending[1]:
            values=['M' if x in self.seed_ids else actions[f't{t}_a{x}'] for x in (a,b)]
            if any(x not in ('Q','M') for x in values): raise ValueError('Illegal convention.')
            payoff=100 if values[0]==values[1] else -50
            for i,x in enumerate((a,b)):
                self.history[x].append([values[i],values[1-i],payoff]); self.scores[x]+=payoff
                self.last[x]=values[i]; self.encounters[x]+=1
                if x in self.last_audits and self.last_audits[x]['delivered_count']: self.bulletin_exposures[x]+=1
            self.seed_contact_count+=int((a in self.seed_ids)!=(b in self.seed_ids))
            events.append(dict(players=[a,b],answers=values,payoff=payoff,channel=channel))
        self.pair_count+=len(events); self.round=t; self.pending=None
        ordinary=[a for a in range(self.n) if a not in self.seed_ids]
        dept_rates=[]; seed_depts=set(self.seed_departments)
        for d in range(self.departments):
            members=[a for a in self.members[d] if a not in self.seed_ids]
            dept_rates.append(sum(self.last[a]=='M' for a in members)/len(members))
        targeted=[dept_rates[d] for d in seed_depts]; other=[dept_rates[d] for d in range(self.departments) if d not in seed_depts]
        success=[e['payoff']==100 for e in events]
        within=[e for e in events if self.roster[e['players'][0]]['department']==self.roster[e['players'][1]]['department']]
        cross=[e for e in events if self.roster[e['players'][0]]['department']!=self.roster[e['players'][1]]['department']]
        return dict(period=t,pairs=len(events),cumulative_pairs=self.pair_count,population_rounds=self.pair_count/self.n,
            voluntary_M_share=sum(self.last[a]=='M' for a in ordinary)/len(ordinary),
            targeted_department_M_share=sum(targeted)/len(targeted) if targeted else None,
            untargeted_department_M_share=sum(other)/len(other) if other else None,
            department_M_share=dept_rates,department_dispersion=max(dept_rates)-min(dept_rates),
            ordinary_coverage=sum(self.encounters[a]>0 for a in ordinary)/len(ordinary),
            ordinary_bulletin_readers=sum(self.bulletin_exposures[a]>0 for a in ordinary),
            role_M_share={role:sum(self.last[a]=='M' for a in ordinary if self.roster[a]['role']==role)/
                max(1,sum(self.roster[a]['role']==role for a in ordinary)) for role in ('employee','manager','executive')},
            seed_contact_count=self.seed_contact_count,coordination=sum(success)/len(success),
            within_department_coordination=sum(e['payoff']==100 for e in within)/len(within) if within else None,
            cross_department_coordination=sum(e['payoff']==100 for e in cross)/len(cross) if cross else None,
            schedule_sha256=digest([e['players'] for e in events]),pair_events=events,
            observation_sha256={str(a):v['view_sha256'] for a,v in self.last_audits.items()})

    def snapshot(self):
        return dict(last_actions=self.last,scores=self.scores,histories=[list(x) for x in self.history],
            encounters=self.encounters,bulletin_exposures=self.bulletin_exposures,
            roster=self.roster,publication_grants=self.publication_grants,memory_policy=self.memory.policy)


class OrganizationEnsemble:
    def __init__(self,worlds,progress=None):
        self.worlds=worlds; self.progress=progress; self.pending={}; self.latest={}
    def describe(self):
        return dict(scenario='organizational_convention_comparison',worlds={wid:w.describe() for wid,w in self.worlds.items()},
            sampling='unique world-prefixed actor streams; common people and contact schedules within each replicate',
            probability_reuse=False)
    def prepare(self,t):
        questions={}; ids={}; self.pending={}
        for wid,world in self.worlds.items():
            batch=world.prepare(t); mapping={f'{wid}__{qid}':qid for qid in batch.questions}
            questions.update({key:batch.questions[qid] for key,qid in mapping.items()})
            ids.update({key:(wid,batch.agent_ids[qid]) for key,qid in mapping.items()})
            self.pending[wid]=mapping
        return DecisionBatch(STATE,questions,ids)
    def advance(self,t,actions,probabilities):
        rows={}
        for wid,mapping in self.pending.items():
            rows[wid]=self.worlds[wid].advance(t,{qid:actions[key] for key,qid in mapping.items()},
                {qid:probabilities[key] for key,qid in mapping.items()})
        self.latest=rows
        if self.progress:self.progress(dict(period=t,means={wid:round(r['voluntary_M_share'],4) for wid,r in rows.items()}))
        return dict(period=t,worlds=rows)


def rule_engine(kind):
    from orgabm.sdk import FunctionEngine
    if kind not in ('uniform','history','notice'): raise ValueError('Unknown explicit rule.')
    def decide(state,q):
        r=json.loads(q['instructions'])
        if kind=='uniform': return {'Q':.5,'M':.5}
        official=[n['value'] for n in r['bulletins'] if n['channel']=='official'] if kind=='notice' else []
        values=official or [h[1] for h in r['history']]
        counts=Counter(values); top=max(counts.values()); choices={k for k,v in counts.items() if v==top}
        return {k:float(k in choices)/len(choices) for k in ('Q','M')}
    return FunctionEngine(decide,name=f'explicit-{kind}-rule')
