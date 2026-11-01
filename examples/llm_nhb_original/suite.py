"""Complete SI B.2 author tournament; replace every original GPT4 action only."""
import ast
import copy
import csv
import hashlib
import itertools
import json
from pathlib import Path
import types

from orgabm.sdk import DecisionBatch
from .sources import ROOT,SCRIPT,CSV,COMMIT,PLAYERS,sources,author_namespace


class GreedyDecisionEngine:
    """Historical argmax comparison; not equivalent to LLM temperature zero.

    Wrap the root's real provider/recovery engine. Its own receipts retain raw
    probabilities; the SDK trace retains the actual one-hot action policy.
    """
    def __init__(self,provider):self.provider=provider
    def decide(self,state,questions):
        result=self.provider.decide(state,questions);out={}
        for q,p in result.items():
            order=questions[q].get('criteria',p)
            best=max(order,key=p.__getitem__);out[q]={k:float(k==best) for k in p}
        return out
    def usage(self):return dict(self.provider.usage(),action_policy='legacy_argmax_comparison_not_temperature_equivalence')


class OriginalTournament:
    def __init__(self,seed=20261030,root=ROOT,action_policy='sample'):
        if action_policy not in ('sample','argmax'):raise ValueError('Unknown action policy.')
        self.action_policy=action_policy
        self.seed=seed;self.root=Path(root);self.provenance=sources(root);self.ns,self.tree=author_namespace(seed,root)
        self.matches=list(itertools.product(PLAYERS,PLAYERS));self.match=0;self.local_round=0;self.sdk_round=0;self.pending=None
        self.last=[['','',''],['','','']];self.histories=['',''];self.totals=[0,0]
        self.rows=[];self.current_rows=[];self.jev_prompts=[];self.jev_schedule=[]

    def describe(self):
        return dict(scenario='nhb2025_original_llm_tournament',doi='10.1038/s41562-025-02172-y',source_commit=COMMIT,
            target='Supplementary B.2 and Table2;full source pd/tft/pd_base_gpt4_tfts_query.py condition set',
            population_per_match=2,rounds_per_match=20,ordered_matches=64,repeated_tournaments=1,
            source_player_order=list(PLAYERS),replacement='Each act_gpt4 call is a fresh Jev choice.No archived GPT4 answers are inputs.',
            substantive_jev_decisions=320,external_decision_stages=300,free_only_matches=49,
            seed=self.seed,seed_note='Author script does not set random.seed;new explicit seed controls NP10/NP20.',
            action_policy=self.action_policy,
            probability_policy=('SDK categorical sampling from raw Jev probabilities; no rescaling (application T=1).'
                if self.action_policy=='sample' else 'Historical argmax comparison; not equivalent to LLM temperature0.'),
            source_llm_temperature=0,jev_api_temperature=None,
            author_quirks=['HTFT starts F in code although SI table says cooperate','prev/prev2/prev3 carry across match boundaries;match order preserved'],
            retained=['Original strategy function ASTs','Original question text,20round horizon and full per-side action/payoff history',
                'Source8x8ordered product,no dropped rule pairs','Source stage payoff matrix and simultaneous actions'],
            source_provenance=self.provenance,
            scope='Full original source-defined SI tournament with decision-model substitution.Not the144game/fiveLLMmain grid or human experiment.')

    def _rule(self,side):
        name=self.matches[self.match][side]
        return self.ns[name]('',self.local_round+1,*self.last[1-side])

    def _commit(self,actions):
        i=self.local_round+1;names=self.matches[self.match];points=self.ns['calculate_points'](*actions)
        for side in (0,1):self.totals[side]+=points[side]
        row=[i,names[0],names[1],actions[0],actions[1],points[0],points[1],self.totals[0],self.totals[1]]
        self.rows.append(row);self.current_rows.append(row)
        for side in (0,1):
            self.last[side]=[actions[side]]+self.last[side][:2]
            self.histories[side]+=f'In round {i}, you chose Option {actions[side]} and the other player chose Option {actions[1-side]}. Thus, you won {points[side]} points and the other player won {points[1-side]} points.\n'
        self.local_round+=1
        if self.local_round==20:
            self.match+=1;self.local_round=0;self.histories=['',''];self.totals=[0,0]

    def _free_matches(self):
        while self.match<64 and 'act_gpt4' not in self.matches[self.match]:
            self._commit([self._rule(0),self._rule(1)])

    def prepare(self,t):
        if self.pending is not None or t!=self.sdk_round+1:raise ValueError('Complete current source transition first.')
        self.current_rows=[];self._free_matches()
        if self.match>=64:raise ValueError('Source tournament already complete.')
        questions={};ids={};self.pending={};i=self.local_round+1
        self.prepared_fixed={}
        for side,name in enumerate(self.matches[self.match]):
            if name=='act_gpt4':
                prompt=self.ns['question']+self.histories[side]+f'You are currently playing round {i}.\n Q: Which Option do you choose, Option J or Option F?\n A: Option'
                q=f'match{self.match}-round{i}-side{side}'
                questions[q]=dict(type='choice',instructions=prompt,criteria={'J':'Option J','F':'Option F'});ids[q]=f'match{self.match}-side{side}'
                self.pending[q]=side;self.jev_prompts.append(prompt)
            else:self.prepared_fixed[side]=self._rule(side)
        return DecisionBatch('Original repeated-game participant action. Only past completed rounds are observed.',questions,ids)

    def advance(self,t,actions,probabilities):
        if self.pending is None or t!=self.sdk_round+1 or set(actions)!=set(self.pending) or any(a not in ('J','F') for a in actions.values()):raise ValueError('Invalid source action commit.')
        selected=dict(self.prepared_fixed)
        for q,side in self.pending.items():selected[side]=actions[q];self.jev_schedule.append(actions[q])
        self._commit([selected[0],selected[1]])
        if t==300:self._free_matches()
        self.sdk_round=t;self.pending=None
        return dict(stage=t,completed_source_game_rounds=len(self.rows),completed_ordered_matches=self.match,
            fresh_jev_decisions=len(self.jev_schedule),new_source_rows=copy.deepcopy(self.current_rows),
            complete=self.match==64,all_rows_sha256=hashlib.sha256(json.dumps(self.rows,separators=(',',':')).encode()).hexdigest())


def original_reference(schedule,prompts=None,seed=20261030,root=ROOT):
    """Execute the unchanged original outer tournament AST with supplied new actions.

    Archived author outputs are not used. This independently checks all 1280
    feedback transitions, rule counterpart actions and exact authored prompts.
    """
    ns,tree=author_namespace(seed,root);cursor=0
    def action(text,*args):
        nonlocal cursor
        if prompts is not None and text!=prompts[cursor]:raise AssertionError('Original prompt differs at call'+str(cursor))
        value=schedule[cursor];cursor+=1;return value
    action.__name__='act_gpt4'
    class Frame:
        def __init__(self,data,columns):self.data=data;self.columns=columns
        def to_csv(self,*args,**kwargs):pass
    ns.update(act_gpt4=action,itertools=itertools,pd=types.SimpleNamespace(DataFrame=Frame))
    start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='player_1')
    exec(compile(ast.Module(body=tree.body[start:],type_ignores=[]),'<unchanged-author-outer-loop-no-api>','exec'),ns)
    if cursor!=len(schedule):raise AssertionError('Not all external actions used.')
    return ns['data']


def build_cases(action_policy='sample'):
    return [dict(id='nhb2025-SI-B2-complete-source-tournament',paper_id='akata2025_nhb',
        environment=OriginalTournament(action_policy=action_policy),rounds=300,seed=20261030,
        condition='complete8x8_20rounds_one_source_tournament')]


def analyze(results):
    case=results[0];metrics=case['result']['metrics'];rows=[r for m in metrics for r in m['new_source_rows']]
    schedule=[]
    for r in rows:
        if r[1]=='act_gpt4':schedule.append(r[3])
        if r[2]=='act_gpt4':schedule.append(r[4])
    ref=original_reference(schedule)
    if rows!=ref:raise AssertionError('Original source rule/feedback transition mismatch.')
    archived=list(csv.DictReader((ROOT/CSV).open(encoding='utf-8')))
    summaries=[]
    for j,(p1,p2) in enumerate(itertools.product(PLAYERS,PLAYERS)):
        block=rows[j*20:(j+1)*20];old=archived[j*20:(j+1)*20]
        summaries.append(dict(source_role1=p1,source_role2=p2,has_jev='act_gpt4' in (p1,p2),
            score1=block[-1][7],score2=block[-1][8],cooperation1=sum(r[3]=='J' for r in block)/20,
            cooperation2=sum(r[4]=='J' for r in block)/20,author_gpt4_archive_score1=int(old[-1]['total1']),
            author_gpt4_archive_score2=int(old[-1]['total2'])))
    return dict(scope='Complete author SI B.2 source condition set;GPT4 substituted byJev,not all main-paper model comparisons.',
        source_rounds=len(rows),ordered_matches=64,actual_external_choices=len(schedule),free_only_matches=49,
        original_outer_loop_all_rows_exact=True,match_summaries=summaries,
        author_archive_note='Archive scores are comparison targets only,never external decision inputs;NP random seed was unpublished.',
        hypothesis='Assess whether cooperation/retaliation against each original opponent persists;no source result is imposed onJev.',
        action_policy=case['result']['environment']['action_policy'],
        limitations=['One source tournament,not new robustness repeats','No human-accuracy claim',
            'Source HTFT/code carryover quirks retained',
            'Jev probabilities are not assumed equivalent to original LLM token probabilities or human population frequencies'])
