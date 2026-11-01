import io
from pathlib import Path
import pickle
import tempfile
import unittest

import pandas as pd

from examples.nc_polarization.archive import NumericSnapshotUnpickler,load_snapshot,metrics
from examples.nc_polarization.model import PolarizationSnapshots,RecordedStateEngine
from orgabm.sdk import run_simulation


class PolarizationArchiveTests(unittest.TestCase):
    def test_unknown_archive_constructor_is_rejected(self):
        class Unsafe:
            def __reduce__(self):return eval,('1+1',)
        with self.assertRaises(pickle.UnpicklingError):NumericSnapshotUnpickler(io.BytesIO(pickle.dumps(Unsafe()))).load()
    def test_named_columns_and_duplicate_edges_preserved(self):
        frame=pd.DataFrame({'target node Id':['1','2','1'],'source node Id':['0','1','0'],
            'target node state':[0,2,0],'source node state':[-2,0,-2]},dtype=object)
        frame.columns=pd.Index(list(frame.columns),dtype=object)
        Path('.buildtmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir='.buildtmp') as tmp:
            file=Path(tmp)/'fixture.pkl';file.write_bytes(pickle.dumps(frame))
            s=load_snapshot(file,population=3)
        self.assertEqual(s['states'],[-2,0,2]);self.assertEqual(metrics(s)['duplicate_edge_rows'],1)
    def test_conflicting_per_actor_state_is_rejected(self):
        frame=pd.DataFrame({'source node Id':[0,1],'target node Id':[1,2],
            'source node state':[-2,1],'target node state':[0,2]},dtype=object)
        frame.columns=pd.Index(list(frame.columns),dtype=object)
        with tempfile.TemporaryDirectory(dir='.buildtmp') as tmp:
            file=Path(tmp)/'fixture.pkl';file.write_bytes(pickle.dumps(frame))
            with self.assertRaisesRegex(ValueError,'Conflicting'):load_snapshot(file,population=3)
    def test_replay_restores_states_and_edges_without_inference(self):
        snapshots=[dict(states=[-2,0,2],edges=[[0,1],[1,2]]),
                   dict(states=[-2,1,2],edges=[[0,2],[1,2],[1,2]])]
        world=PolarizationSnapshots('fixture',snapshots)
        result=run_simulation(world,RecordedStateEngine(world),rounds=1,seed=7)
        self.assertEqual(world.current,snapshots[-1]);self.assertEqual(result['decisions'],3)
        self.assertEqual(result['usage']['actual_model_api_calls'],0)


if __name__=='__main__':unittest.main()
