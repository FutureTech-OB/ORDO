"""Author-derived network mechanics; generated text is endogenous, never archived.

Upstream MIT: tsinghua-fib-lab/LLM_for_Polarization, pinned in source_manifest.json.
See UPSTREAM_LICENSE.txt. The research model is changed, as documented in README.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import random
from concurrent.futures import ThreadPoolExecutor

from orgabm.sdk import DecisionBatch
from examples.nc_polarization.archive import load_snapshot, metrics

TOPIC = dict(environment='Sociopolitical', topic='stricter or looser Gun Control',
    S_m2='Strongly Support Weaker Gun Control', S_m1='Support Weaker Gun Control',
    S_0='Neutral', S_p1='Support Stricter Gun Control', S_p2='Strongly Support Stricter Gun Control',
    S_m2_e='weaker Gun Control is absolutely better than stricter Gun Control in all aspects',
    S_m1_e='weaker Gun Control and stricter Gun Control both have ups and downs, but weaker Gun Control have a slight edge.',
    S_0_e="doesn't lean towards or favor either the weaker or stricter Gun Control.",
    S_p1_e='stricter Gun Control and weaker Gun Control both have ups and downs, but stricter Gun Control have a slight edge.',
    S_p2_e='stricter Gun Control is absolutely better than weaker Gun Control in all aspects')
LABELS = {str(s): TOPIC[k] for s,k in zip(range(-2,3),('S_m2','S_m1','S_0','S_p1','S_p2'))}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


class CapturedPrompt(BaseException):
    def __init__(self,prompt): self.prompt=prompt


class AuthorPrompts:
    """Compile only inspected, hash-pinned prompt functions, with no author imports/network."""
    names={'initialize_tweet','LLM_update_profile_5_and_LLM_get_reason','LLM_reconnect','LLM_persuade'}
    def __init__(self,source):
        def capture(prompt): raise CapturedPrompt(prompt)
        tree=ast.parse(Path(source).read_text(encoding='utf-8'))
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in self.names]
        if {n.name for n in nodes}!=self.names: raise ValueError('Pinned author prompt functions missing.')
        self.namespace={'get_completion_1':capture,'json':json}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),self.namespace)

    def get(self,name,*args):
        try: self.namespace[name](*copy.deepcopy(args))
        except CapturedPrompt as capture: return capture.prompt
        raise ValueError('Author prompt failed before capture.')


def selected_text(messages,previous):
    # Preserve the author's -0 indexing: first item, then last, second-last, etc.
    new=[m for m in messages[-300:] if m not in previous[-300:]]
    old=[m for m in messages[-300:] if m in previous[-300:]]
    join=lambda seq: ''.join(seq[-i]['content'] for i in range(min(5,len(seq))))[-1000:]
    return join(new),join(old)


class HybridPolarization:
    def __init__(self,snapshot,prompts,generator,*,seed=20261030,epochs=40,workers=32):
        self.initial=copy.deepcopy(snapshot);self.n=len(snapshot['states']);self.prompts=prompts
        self.generator=generator;self.rng=random.Random(seed);self.seed=seed
        self.epochs=epochs;self.workers=workers;self.step=0;self.epoch=0;self.pending=None
        self.users=[dict(profile=dict(side=s,p_side=s,reasons='',patience=0),messages=[],previous=[],friends=[])
                    for s in snapshot['states']]
        for a,b in snapshot['edges']:self.users[a]['friends'].append(b)
        self.active=[];self.seeds=[];self.initialized=False;self.trajectory=[]
        self.counts=dict(seed_posts=0,opinion_updates=0,relationship_decisions=0,
                         speaking_decisions=0,generated_posts=0,rewired_edges=0,delivered_messages=0)

    def describe(self):
        return dict(scenario='nc_polarization_fresh_hybrid',doi='10.1038/s41467-026-78228-y',
            population=self.n,epochs=self.epochs,topic='Gun Control',source_initial_sha256=digest(self.initial),
            source_condition='archived baseline Gun Control epoch 0; original 1000/40 main-figure dimensions',
            decision_units='stance per person, continue per outgoing edge slot, speak per unique directed pair',
            modifications=['Jev samples stance/continue/speak; conditional fresh LLM reasons/posts replace joint generation',
                'Missing author patience initialized to 0 for all people; not inferred from archived data',
                'Deterministic ascending actor/pair order replaces Python object-set order',
                'Omit overwritten persuasion calls; retain exact final author prompt',
                'Modern explicitly pinned generation backbone; not original GPT-3.5 trajectories'],
            source_quirks_preserved=['-0 message indexing','sequential spread and target=0 truthiness',
                'rewiring excludes self but allows duplicate outgoing edges','reasons and fresh posts feed next period'],
            initial_message_status='Source initialization input has empty messages. Fresh 10% seed posts are generated.',
            evidence='One new hybrid model arm; not pure Jev, not a full-paper replication, not human validation.')

    def _generate(self,tasks):
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(lambda row:self.generator.generate(*row),tasks))

    def _seed(self):
        self.seeds=[a for a in range(self.n) if self.rng.random()>.9]
        tasks=[(f'initial_post:a{a}','seed',self.prompts.get('initialize_tweet',self.users[a]['profile'],TOPIC))
               for a in self.seeds]
        for a,text in zip(self.seeds,self._generate(tasks)):
            u=self.users[a];u['messages'].append(dict(source=a,target=None,content=text));u['profile']['reasons']=text
        self.counts['seed_posts']=len(tasks);self.initialized=True

    def _spread(self):
        affected=set()
        # Same sequential iteration and equality-based membership as author spread().
        for a,u in enumerate(self.users):
            difference=[m for m in u['messages'][-300:] if m not in u['previous'][-300:]]
            for message in difference:
                if message['source']!=a:continue
                targets=[message['target']] if message['target'] else [b for b in u['friends'] if b!=a]
                for b in targets:
                    delivered=message if message['target'] else dict(source=a,target=b,content=message['content'])
                    self.users[b]['messages'].append(copy.deepcopy(delivered));affected.add(b)
                    self.counts['delivered_messages']+=1
            u['previous']=copy.deepcopy(u['messages'])
        return sorted(affected)

    def prepare(self,t):
        if self.pending is not None or t!=self.step+1:raise ValueError('Prepare/commit sequential stages.')
        if not self.initialized:self._seed()
        if t==1:phase='seed_stance';epoch=0;units=[(a,) for a in self.seeds]
        else:
            epoch=(t-2)//3+1;phase=('stance','continue','speak')[(t-2)%3]
            if epoch>self.epochs:raise ValueError('Past declared horizon.')
            if phase=='stance':self.active=self._spread();units=[(a,) for a in self.active]
            elif phase=='continue':units=[(a,i,b) for a in self.active for i,b in enumerate(self.users[a]['friends'])]
            else:units=sorted({(a,b) for a in self.active for b in self.users[a]['friends']})
        questions={};mapping={}
        for unit in units:
            a=unit[0];u=self.users[a];qid=f'e{epoch}:{phase}:'+':'.join(map(str,unit))
            if phase in ('stance','seed_stance'):
                new,old=selected_text(u['messages'],u['previous'])
                prompt=self.prompts.get('LLM_update_profile_5_and_LLM_get_reason',u['profile'],new,old,TOPIC)
                criteria=LABELS.copy()
            elif phase=='continue':
                prompt=self.prompts.get('LLM_reconnect',u['profile'],self.users[unit[2]]['profile'],TOPIC)
                criteria={'yes':'Continue sharing with this person.','no':'Stop this relationship and reconnect randomly.'}
            else:
                text=''.join(u['messages'][-i]['content'] for i in range(min(5,len(u['messages']))))[-1000:]
                prompt=self.prompts.get('LLM_persuade',u['profile'],text,self.users[unit[1]]['profile'],TOPIC)
                criteria={'yes':'Send a persuasive message to this friend.','no':'Send no message.'}
            questions[qid]=dict(type='choice',instructions=prompt,criteria=criteria);mapping[qid]=unit
        self.pending=(t,epoch,phase,mapping,copy.deepcopy(questions))
        return DecisionBatch('Independent local decisions. Use only each question; do not infer a population target.',
                             questions,{q:':'.join(map(str,u)) for q,u in mapping.items()})

    def advance(self,t,actions,probabilities):
        if self.pending is None or self.pending[0]!=t:raise ValueError('Prepare this stage first.')
        _,epoch,phase,mapping,questions=self.pending
        if set(actions)!=set(mapping):raise ValueError('Mismatched action IDs.')
        if phase in ('stance','seed_stance'):
            tasks=[]
            for qid,(a,) in mapping.items():
                side=int(actions[qid]);u=self.users[a];u['profile']['side']=side
                u['profile']['tendency']=LABELS[str(side)]
                prompt=questions[qid]['instructions']+'\nThe standpoint has ALREADY been selected: '+LABELS[str(side)]+'. '
                prompt+='Keep that tendency exactly. Return JSON with tendency and reasons (around 50 words); explain only this selected standpoint.'
                tasks.append((qid+':reason','reason',prompt))
            for (qid,(a,)),reason in zip(mapping.items(),self._generate(tasks)):self.users[a]['profile']['reasons']=reason
            self.counts['opinion_updates']+=len(mapping)
        elif phase=='continue':
            for qid,(a,slot,b) in mapping.items():
                if actions[qid]=='no':
                    friends=self.users[a]['friends'];friends.remove(b)
                    new=self.rng.randint(0,self.n-1)
                    while new==a:new=self.rng.randint(0,self.n-1)
                    friends.append(new);self.counts['rewired_edges']+=1
            self.counts['relationship_decisions']+=len(mapping)
        else:
            spoken=[(qid,unit) for qid,unit in mapping.items() if actions[qid]=='yes']
            tasks=[(qid+':post','post',questions[qid]['instructions']+
                "\nYou have ALREADY chosen will=yes. Return JSON with will=yes and a fresh persuasive message of around 50 words.") for qid,_ in spoken]
            for (qid,(a,b)),text in zip(spoken,self._generate(tasks)):
                self.users[a]['messages'].append(dict(source=a,target=b,content=text))
            self.counts['speaking_decisions']+=len(mapping);self.counts['generated_posts']+=len(spoken)
        self.step=t;self.epoch=epoch;self.pending=None
        result=dict(epoch=epoch,phase=phase,**self.current_metrics(),counts_cumulative=self.counts.copy(),
                    state_sha256=self.state_hash(),stage_decisions=len(mapping))
        if phase in ('seed_stance','speak'):
            self.trajectory.append(result)
            for u in self.users:u['profile']['p_side']=u['profile']['side']
        return result

    def snapshot(self):
        return dict(states=[u['profile']['side'] for u in self.users],
                    edges=[[a,b] for a,u in enumerate(self.users) for b in u['friends']])

    def current_metrics(self):
        return metrics(self.snapshot())

    def state_hash(self):
        return digest(self.users)


def load_initial(root):
    return load_snapshot(Path(root)/'source_data/Gun Control/epoch_run0.pkl',population=1000)
