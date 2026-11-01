import io
import pickle
from pathlib import Path
import unittest

import numpy as np

from examples.ncs_additional_mobility.model import AuthorNavigation,NumericGraphUnpickler,PedNavTrips,native_engine
from examples.ncs_additional_mobility.run import reference
from examples.ncs_additional_mobility.sources import DEFAULT
from orgabm.sdk import run_simulation


class SourceBoundary(unittest.TestCase):
    def test_reject_external_globals(self):
        try:import igraph
        except ImportError:self.skipTest('Optional igraph dependency absent.')
        with self.assertRaises(pickle.UnpicklingError):NumericGraphUnpickler(io.BytesIO(pickle.dumps(Path('.')))).load()


class NativePaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:import igraph
        except ImportError:raise unittest.SkipTest('Install optional igraph==0.11.9.')
        if not (DEFAULT/'pednav/main.py').exists():raise unittest.SkipTest('Download pinned public sources first.')
        cls.author=AuthorNavigation()

    def test_native_direct_vs_sdk(self):
        for kind in ('vector','shortest'):
            c=dict(kind=kind,sigma=.7,seed=7,trip_limit=3)
            native,_=reference(self.author,c);env=PedNavTrips(self.author,**c)
            result=run_simulation(env,native_engine(),rounds=3,seed=7)
            self.assertEqual(env.routes,native);self.assertEqual(result['decisions'],3)
            self.assertTrue(all(x['detour_ratio']>=1-1e-10 for x in env.trajectory))

    def test_restore_random_state(self):
        old=np.random.get_state();trip=self.author.human[0]
        self.author.route('vector',trip['origin'],trip['destination'],.7,7)
        new=np.random.get_state()
        self.assertEqual(old[0],new[0]);np.testing.assert_array_equal(old[1],new[1]);self.assertEqual(old[2:],new[2:])

    def test_invalid_commit_preserves_world(self):
        env=PedNavTrips(self.author,trip_limit=1);env.prepare(1)
        with self.assertRaises(ValueError):env.advance(1,{'trip-1':'wrong'},{})
        self.assertEqual(env.routes,[]);self.assertEqual(env.round,0)


if __name__=='__main__':unittest.main()
