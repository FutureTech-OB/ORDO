"""State/network archive replay through ORDO, not a fresh LLM replication."""
import copy
import hashlib
import json

from orgabm.sdk import DecisionBatch
from .archive import metrics


def digest(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class PolarizationSnapshots:
    def __init__(self,topic,snapshots):
        if len(snapshots)<2:raise ValueError('At least two snapshots are required.')
        n=len(snapshots[0]['states'])
        if any(len(s['states'])!=n for s in snapshots):raise ValueError('Population changed between snapshots.')
        self.topic=topic;self.snapshots=copy.deepcopy(snapshots);self.current=copy.deepcopy(snapshots[0]);self.round=0
        self.pending=None;self.n=n;self.trajectory=[self.current]
    def describe(self):
        return dict(scenario='nc_polarization_snapshot_replay',topic=self.topic,population=self.n,
            periods=len(self.snapshots)-1,doi='10.1038/s41467-026-78228-y',
            evidence='archived opinions and directed edge rows; text generation and original inference contexts are absent',
            initial_state_sha256=digest(self.current),probability_reuse=False)
    def prepare(self,t):
        if self.pending is not None or t!=self.round+1 or t>=len(self.snapshots):raise ValueError('Invalid archive period.')
        outgoing={a:[] for a in range(self.n)}
        for a,b in self.current['edges']:outgoing[a].append([b,self.current['states'][b]])
        self.pending=t
        questions={f't{t}_a{a}':dict(type='choice',instructions=json.dumps(dict(actor=a,prior_opinion=self.current['states'][a],
            prior_outgoing_neighbors=outgoing[a]),separators=(',',':')),criteria={str(s):f'Recorded opinion {s}' for s in range(-2,3)})
            for a in range(self.n)}
        return DecisionBatch('Archived-state reconstruction. The recorded-data engine supplies the next observed opinion. '
            'This is not an opinion-prediction prompt or a reconstruction of missing conversations.',questions,
            {qid:a for a,qid in enumerate(questions)})
    def advance(self,t,actions,probabilities):
        if t!=self.pending:raise ValueError('Prepare this archive period first.')
        restored=[int(actions[f't{t}_a{a}']) for a in range(self.n)]
        target=self.snapshots[t]
        if restored!=target['states']:raise ValueError('Recorded-state replay did not reproduce the source opinions.')
        # Topology is supplied by the archive. No invented reconnection decisions.
        self.current=dict(states=restored,edges=copy.deepcopy(target['edges']))
        self.round=t;self.pending=None;self.trajectory.append(self.current)
        return dict(epoch=t,**metrics(self.current),state_and_edges_sha256=digest(self.current))


class RecordedStateEngine:
    def __init__(self,world):self.world=world
    def decide(self,state,questions):
        t=self.world.pending
        return {qid:{str(s):float(s==self.world.snapshots[t]['states'][a]) for s in range(-2,3)}
            for a,qid in enumerate(questions)}
    def usage(self):return dict(engine='archived-next-state',actual_model_api_calls=0,
        accounting='SDK assignments count restored member states, not original LLM inference calls.')
