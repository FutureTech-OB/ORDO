import io
import json
import unittest

from examples.llm_abm_cookbook.resume_behavior import PrefixThenLive


class Fresh:
    def __init__(self): self.calls=0
    def decide(self,state,questions):
        self.calls+=1
        return {qid:{'Q':0,'M':1} for qid in questions}


class BehavioralRecovery(unittest.TestCase):
    def test_completed_prefix_does_not_resubmit_provider_inference(self):
        q={'old':{'instructions':'choose','criteria':{'Q':'Q','M':'M'}}}
        record=dict(state='old state',questions=q,probabilities={'old':{'Q':1,'M':0}})
        fresh=Fresh(); engine=PrefixThenLive(io.StringIO(json.dumps(record)+'\n'),1,fresh,{})
        self.assertEqual(engine.decide('old state',q),record['probabilities'])
        self.assertEqual(fresh.calls,0)
        self.assertEqual(engine.decide('new state',{'new':q['old']}),{'new':{'Q':0,'M':1}})
        self.assertEqual(fresh.calls,1)

    def test_checkpoint_input_mismatch_fails_before_live_request(self):
        record=dict(state='recorded',questions={},probabilities={})
        fresh=Fresh(); engine=PrefixThenLive(io.StringIO(json.dumps(record)+'\n'),1,fresh,{})
        with self.assertRaises(AssertionError): engine.decide('changed',{})
        self.assertEqual(fresh.calls,0)


if __name__=='__main__': unittest.main()
