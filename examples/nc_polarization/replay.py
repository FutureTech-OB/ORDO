"""Check the portable state/network archive without downloads or API keys."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

from orgabm.sdk import run_simulation
from .archive import metrics
from .model import PolarizationSnapshots,RecordedStateEngine,digest


def replay(evidence):
    root=Path(evidence)
    manifest=json.loads((root/'replay_manifest.json').read_text(encoding='utf-8'))
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    path=root/manifest['file']
    if path.parent.resolve()!=root.resolve():raise ValueError('Invalid archive payload path.')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('Archive checksum mismatch.')
    if hashlib.sha256((root/'source_manifest.json').read_bytes()).hexdigest()!=manifest['sources_sha256']:
        raise ValueError('Source manifest checksum mismatch.')
    for file,sha in report['source_hashes'].items():
        if hashlib.sha256(Path(__file__).with_name(file).read_bytes()).hexdigest()!=sha:
            raise ValueError('Recorded cookbook code changed: '+file)
    with gzip.open(path,'rb') as stream:raw=stream.read(40_000_001)
    if len(raw)>40_000_000:raise ValueError('Unexpectedly large portable archive.')
    payload=json.loads(raw)
    with (root/'trajectories.csv').open(encoding='utf-8') as stream:
        rows={(r['topic'],int(r['epoch'])):r for r in csv.DictReader(stream)}
    verified={}
    for topic,snapshots in payload.items():
        if len(snapshots)!=41 or any(len(s['states'])!=1000 for s in snapshots):raise ValueError('Unexpected archive dimensions.')
        for snapshot in snapshots:
            if any(type(v) is not int or v not in range(-2,3) for v in snapshot['states']):raise ValueError('Invalid archived opinion.')
            if not 1<=len(snapshot['edges'])<=10000 or any(len(e)!=2 or any(type(x) is not int or not 0<=x<1000 for x in e) for e in snapshot['edges']):
                raise ValueError('Invalid archived edge.')
        world=PolarizationSnapshots(topic,snapshots)
        result=run_simulation(world,RecordedStateEngine(world),rounds=40,seed=7)
        if [digest(s) for s in world.trajectory]!=[digest(s) for s in snapshots]:raise AssertionError('Source-state restoration mismatch.')
        for epoch,s in enumerate(world.trajectory):
            row=rows[(topic,epoch)];m=metrics(s)
            for key,value in m.items():
                if key=='counts':continue
                if float(row[key])!=value:raise AssertionError('Exported trajectory mismatch: '+key)
        if metrics(world.current)!=report['topics'][topic]['final']:raise AssertionError('Final source metric mismatch.')
        verified[topic]=dict(periods=40,restored_member_states=result['decisions'],all_states_and_edge_rows_exact=True,
            all_exported_metrics_exact=True,actual_model_api_calls=0)
        print(json.dumps({topic:verified[topic]}),flush=True)
    return verified


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',default='docs/nc_polarization/results')
    replay(p.parse_args().evidence)
