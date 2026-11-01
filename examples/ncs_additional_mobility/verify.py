"""Read-only verification of frozen source and archived output hashes."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    root=Path(root);data=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if data['status']!='complete':raise ValueError('Incomplete run.')
    for file,sha in data['source_hashes'].items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=sha:raise ValueError('Source changed: '+file)
    for file,sha in data['output_sha256'].items():
        if hashlib.sha256((root/file).read_bytes()).hexdigest()!=sha:raise ValueError('Output changed: '+file)
    if not all(c['all_paths_exact'] for c in data['cases']):raise ValueError('Native mismatch.')
    return dict(status='verified',cases=len(data['cases']),native_route_samples=data['native_route_samples'],
        sdk_control_actions=data['sdk_control_actions'],source_files=len(data['source_hashes']),output_files=len(data['output_sha256']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    print(json.dumps(verify(p.parse_args().root),indent=2))
