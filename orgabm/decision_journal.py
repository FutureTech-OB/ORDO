"""Recover successful decisions for the exact original events after interruption.

This is journal recovery, never a cache of probabilities for other agents/states.
"""
import copy
import json
from pathlib import Path

from .sdk import validate_decisions


class DecisionJournal:
    def __init__(self,paths):
        self.entries={}
        for path in paths:
            with Path(path).open(encoding='utf-8') as stream:
                for line in stream:
                    row=json.loads(line); request=row['request']; response=row['response']
                    model=response.get('model','')
                    if not isinstance(model,str) or not (model==request['model'] or model.startswith(request['model']+'-')):
                        raise ValueError('Cannot recover a response from an unexpected model family.')
                    answers={qid:a.get('probabilities') for qid,a in response['answers'].items()}
                    probabilities=validate_decisions(request['questions'],answers)
                    for qid,q in request['questions'].items():
                        entry=dict(state=request['state'],question=q,probabilities=probabilities[qid])
                        if qid in self.entries:
                            previous=self.entries[qid]
                            if previous['state']!=entry['state'] or previous['question']!=q:
                                raise ValueError('A journal event ID was reused for a different input.')
                            # Keep the earliest valid response; never select retrospectively by outcome.
                        else:self.entries[qid]=entry

    def recover(self,state,questions):
        found={}; missing={}
        for qid,q in questions.items():
            if qid not in self.entries:missing[qid]=q;continue
            row=self.entries[qid]
            if state!=row['state'] or q!=row['question']:
                raise ValueError('Journal input differs from the original event; recovery stopped before inference.')
            found[qid]=copy.deepcopy(row['probabilities'])
        return found,missing


class ResumeDecisionEngine:
    def __init__(self,provider,journal,prefix_stream,completed_periods):
        self.provider=provider; self.journal=journal;self.stream=prefix_stream;self.completed=completed_periods
        self.step=0;self.prefix_decisions=0;self.partial_decisions=0;self.fresh_decisions=0
    def decide(self,state,questions):
        self.step+=1
        if self.step<=self.completed:
            row=json.loads(next(self.stream))
            if state!=row['state'] or questions!=row['questions']:
                raise ValueError('Checkpoint input differs; no fresh inference submitted for this step.')
            self.prefix_decisions+=len(questions)
            return row['probabilities']
        found,missing=self.journal.recover(state,questions)
        self.partial_decisions+=len(found)
        if missing:
            fresh=self.provider.decide(state,missing); found.update(fresh);self.fresh_decisions+=len(missing)
        return found
    def usage(self):
        return dict(self.provider.usage(),offline_prefix_decisions=self.prefix_decisions,
            recovered_original_pending_decisions=self.partial_decisions,new_decisions_after_resume=self.fresh_decisions)
