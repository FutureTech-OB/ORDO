import io
from pathlib import Path
import pickle
import unittest
from examples.ncs_colocation.sources import RestrictedUnpickler,DEFAULT_CACHE,checkout
from examples.ncs_colocation.model import ColocationEnvironment,native_engine,reference
from orgabm.sdk import run_simulation


class ColocationTests(unittest.TestCase):
    def test_pickle_rejects_arbitrary_globals(self):
        with self.assertRaises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(b'cos\nsystem\n.')).load()

    @unittest.skipUnless((Path(DEFAULT_CACHE)/'code/SimulationsSubmission.ipynb').exists(),'Public source cache not downloaded.')
    def test_original_kernel_daily_equivalence_and_golden_bridges(self):
        config=dict(population=100,seed=7,policy='remote_then_return',lengths=(2,3,2))
        root=checkout();world=ColocationEnvironment(root,**config)
        result=run_simulation(world,native_engine(),rounds=7,seed=7)
        author=reference(root,**config)
        self.assertEqual(world.graphs,author['graphs'])
        self.assertEqual(world.snapshot()['memory'],author['memory'])
        self.assertEqual([r['weak_ties'] for r in world.records],[40,48,40,40,33,35,37])
        self.assertEqual(result['decisions'],0)
        self.assertEqual(world.native_edge_draws,500)
        self.assertEqual([r['phase'] for r in world.records],[0,0,1,1,1,2,2])

    def test_invalid_public_demo_configuration(self):
        with self.assertRaises(ValueError):ColocationEnvironment('unused',population=1000)


if __name__=='__main__':unittest.main()
