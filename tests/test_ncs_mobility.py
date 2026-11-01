import copy
import json
from pathlib import Path
import unittest

from examples.ncs_mobility.model import NativeMobility,native_engine,validate,metrics
from examples.ncs_mobility.run import reference
from examples.ncs_mobility.build import DEFAULT
from orgabm.sdk import run_simulation


class MobilityConfiguration(unittest.TestCase):
    def test_bounds_and_native_mode_are_explicit(self):
        for config in ({'agents':0},{'rounds':1001},{'memory':'yes'},{'rho0':-1},{'seed':2**31}):
            with self.assertRaises(ValueError):validate(config)


@unittest.skipUnless((DEFAULT/'cmm_bridge.dll').exists() and (DEFAULT/'cmm_reference.exe').exists(),
                     'Build the pinned Windows/PPL author kernel with examples.ncs_mobility.build first.')
class NativeMobilityIntegration(unittest.TestCase):
    def test_native_reference_matches_sdk_for_memory_and_coupling(self):
        for memory,rho0 in [(True,1e-12),(False,10.0)]:
            config=validate(dict(agents=16,rounds=5,seed=11,memory=memory,rho0=rho0));ref=reference(config,DEFAULT)
            env=NativeMobility(config)
            try:
                result=run_simulation(env,native_engine(),rounds=5,seed=11)
                self.assertEqual(result['metrics'],ref['metrics']);self.assertEqual(env.final_values,ref['final'])
                self.assertEqual(result['decisions'],5)
                self.assertEqual(sum(x['native_agent_updates'] for x in result['metrics']),80)
            finally:env.close()
    def test_invalid_commit_does_not_advance_native_world(self):
        config=validate(dict(agents=8,rounds=1,seed=7));env=NativeMobility(config)
        try:
            env.prepare(1)
            with self.assertRaises(ValueError):env.advance(1,{'period-1':'wrong'}, {})
            self.assertEqual(env.round,0)
            env.advance(1,{'period-1':'native_step'}, {})
            ref=reference(config,DEFAULT)
            self.assertEqual(env.final_values,ref['final'])
        finally:env.close()
    def test_corrupted_population_ledger_is_rejected(self):
        config=validate(dict(agents=8,rounds=1));ref=reference(config,DEFAULT);state=copy.deepcopy(ref['final'])
        # The first sparse population array begins with count, site and population.
        state[4]+=1
        with self.assertRaises(AssertionError):metrics(state,config)
    def test_native_global_state_cannot_be_silently_shared(self):
        env=NativeMobility(validate(dict(agents=8,rounds=1)))
        try:
            with self.assertRaises(RuntimeError):NativeMobility(validate(dict(agents=9)))
            result=run_simulation(env,native_engine(),rounds=1,seed=7)
            self.assertEqual(result['metrics'][0]['population'],8)
        finally:env.close()


if __name__=='__main__':unittest.main()
