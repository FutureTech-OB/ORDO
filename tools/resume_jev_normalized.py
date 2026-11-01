"""Resume the frozen v1 runner when tuple metadata became JSON arrays.

Only descriptive metadata is canonicalized. World preparation, actions,
sampling, source validation, protocol and allowances remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.jev_validation import run


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--output',required=True)
    parser.add_argument('--group',required=True)
    args,unknown=parser.parse_known_args()
    if '--resume' not in unknown:
        raise ValueError('This helper only resumes an existing failed run.')
    root=Path(args.output)
    frozen=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
    if frozen['source_hashes']!=run.source_hashes(args.group):
        # Imports used by the cases must be loaded before comparing sources.
        import importlib
        importlib.import_module(f'examples.jev_{args.group}.suite').build_cases()
    if frozen['source_hashes']!=run.source_hashes(args.group):
        raise ValueError('The original source hashes differ; metadata normalization cannot bypass this.')
    original=run.Ensemble.describe
    run.Ensemble.describe=lambda self:json.loads(json.dumps(original(self),allow_nan=False))
    run.save(root/'metadata-normalization-recovery.json',dict(
        reason='Tuple-valued descriptive metadata was serialized as JSON arrays; canonical JSON is equal.',
        change='Only Ensemble.describe return representation normalized; no action, probability, protocol or allowance change.',
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        frozen_runner_sha256=hashlib.sha256(Path(run.__file__).read_bytes()).hexdigest()))
    run.main()
