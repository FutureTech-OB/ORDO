"""De Marzo 2026 Fig.2 N=50 arm: the original count-based memoryless process."""
import hashlib
import json
import random
import string
from orgabm.sdk import DecisionBatch

COMMIT='889567cc50ca708e976bbf8a3ca5c010743f40c3'
CODE_BLOB='c60d23995a22ea2aa114cb2e5e67e909448811d6'


class OriginalMajority:
    def __init__(self,seed):
        self.n=50;self.seed=seed;self.na=25;self.updates=0;self.rng=random.Random(seed)
        self.pending=None;self.done=False;self.first_consensus=None;self.last=None

    def describe(self):
        return dict(paper_doi='10.1126/sciadv.aea6091',figure='Fig.2 N=50 original condition; one replacement model arm',
            source_commit=COMMIT,source_code_blob=CODE_BLOB,agents=50,initial_Na=25,initial_m=0,
            max_updates=500,max_population_time=10,source_repetitions=20,seed=self.seed,
            memory=False,reward=False,source_temperature=.2,
            observed='All N-1 other opinions with fresh two-character alphanumeric names, shuffled order and k/z label flip.',
            hidden='Own previous opinion, persistent identities, previous steps, separately reported population counts, target consensus.',
            model_substitution='Jev probability output and seeded categorical action draw replace original text generation at T=.2; no LLM temperature equivalence claimed.',
            source_reconciliation='Paper independent m0=0 trials used. Public script has missing T argument and carries Na between trials; those driver inconsistencies are not replicated.',
            alias_order='Generated random name set sorted before the original synchronized shuffle for process-independent replay; source used unordered list(set).')

    def prepare(self,t):
        if self.pending is not None:raise ValueError('Commit previous choice first.')
        if self.done:
            return DecisionBatch('No active individual after original consensus/horizon stopping.',{}, {})
        if t!=self.updates+1:raise ValueError('Sequential asynchronous updates are required.')
        chars=string.ascii_letters+string.digits;names=set()
        while len(names)<self.n:names.add(''.join(self.rng.choice(chars) for _ in range(2)))
        names=sorted(names)
        labels=['k','z'] if self.rng.random()<=.5 else ['z','k']
        opinions=[labels[0]]*self.na+[labels[1]]*(self.n-self.na)
        self.rng.shuffle(opinions);selected=self.rng.randint(0,self.n-1);previous=opinions[selected]
        opinions.pop(selected);names.pop(selected)
        order=list(range(self.n-1));self.rng.shuffle(order)
        peers=[(names[i],opinions[i]) for i in order]
        # Original author-code prompt, including its spellings and output wrapper.
        intro=('Below you can see the list of all your friends toghether with the opinion they support.\n'
               '        You must reply with the opinion you want to support.\n'
               '        The opinion must be reported between square brakets.')
        prompt=intro+'\n'+''.join(f'{name}: {opinion}\n' for name,opinion in peers)+'. \n        Reply only with the opinion you want to support, between square brakets.'
        qid=f't{t}_slot{selected}';self.pending=(t,qid,labels,previous,selected)
        return DecisionBatch('A memoryless individual chooses one opinion using only the displayed friends.',
            {qid:dict(type='choice',instructions=prompt,criteria={x:f'Support opinion {x}.' for x in labels})},
            {qid:selected})

    def advance(self,t,actions,probabilities):
        if self.done:
            if actions or probabilities:raise ValueError('A stopped world must submit no judgments.')
            return dict(self.last,padding=True)
        if self.pending is None or self.pending[0]!=t:raise ValueError('Prepare current update first.')
        _,qid,labels,previous,selected=self.pending
        if set(actions)!={qid} or actions[qid] not in labels:raise ValueError('Unexpected original opinion action.')
        pre_m=(2*self.na-self.n)/self.n;choice=actions[qid]
        if choice!=previous:self.na+=1 if choice==labels[0] else -1
        self.updates=t;self.pending=None;m=(2*self.na-self.n)/self.n
        if abs(m)==1 and self.first_consensus is None:self.first_consensus=t
        self.done=abs(m)==1 or t==500
        self.last=dict(update=t,population_time=t/50,positive_count=self.na,negative_count=50-self.na,
            mean_opinion=m,coordination=abs(m),source_preupdate_mean_opinion=pre_m,
            consensus=abs(m)==1,first_consensus_update=self.first_consensus,
            stop='consensus' if abs(m)==1 else ('horizon' if t==500 else None),padding=False)
        return dict(self.last)
