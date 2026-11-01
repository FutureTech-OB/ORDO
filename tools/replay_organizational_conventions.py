"""Offline replay of exported organizational decisions; no API credential needed."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


def digest(value):
    # Keep insertion order, including choice presentation order, in the evidence.
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def portable_source_hashes(sources):
    repo=Path(__file__).resolve().parents[1]
    return {Path(name).resolve().relative_to(repo).as_posix():sha for name,sha in sources.items()}


def export_replay(root,out,report):
    """Keep probabilities and hashes, regenerating bulky local contexts on replay."""
    manifest=dict(format='ordo-organizational-replay-v1',sampling_seed=202610,
        frozen_plan=report['frozen_plan'],source_hashes=portable_source_hashes(report['source_hashes']),engines={})
    repo=Path(__file__).resolve().parents[1]
    manifest['source_lf_sha256']={name:hashlib.sha256((repo/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        for name in manifest['source_hashes']}
    for engine,group in report['groups'].items():
        trace=report.get('active_jev_trace','jev') if engine=='jev' else engine
        target=out/f'{engine}-replay.jsonl.gz'
        with (root/trace/'events.jsonl').open(encoding='utf-8') as source,gzip.open(target,'wt',encoding='utf-8',newline='\n') as dest:
            for line in source:
                row=json.loads(line)
                compact=dict(round=row['round'],input_sha256=digest([row['state'],row['questions']]),
                    probabilities=row['probabilities'],metrics_sha256=digest(row['metrics']))
                dest.write(json.dumps(compact,separators=(',',':'),allow_nan=False)+'\n')
        snapshots=root/('jev-snapshots' if engine=='jev' else f'{engine}-snapshots')
        states={r['world']:digest(json.loads((snapshots/f"{r['world']}.json").read_text(encoding='utf-8'))) for r in group['worlds']}
        manifest['engines'][engine]=dict(file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            periods=report['frozen_plan']['preview']['periods'],decisions=group['decisions'],final_states_sha256=states)
    (out/'replay_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def replay(evidence,engines=None):
    repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
    from orgabm.sdk import run_simulation
    from examples.organizational_conventions.model import OrganizationEnsemble
    from examples.organizational_conventions.run import make_worlds
    manifest=json.loads((evidence/'replay_manifest.json').read_text(encoding='utf-8'))
    if manifest['format']!='ordo-organizational-replay-v1':raise ValueError('Unsupported replay format.')
    for name,sha in manifest['source_hashes'].items():
        file=Path(name)
        if file.is_absolute():file=repo/'examples'/'organizational_conventions'/file.name
        else:file=repo/file
        raw=file.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha and hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()!=manifest.get('source_lf_sha256',{}).get(name):
            raise ValueError('Recorded experiment source changed: '+name)
    output={}
    for engine,meta in manifest['engines'].items():
        if engines and engine not in engines:continue
        file=evidence/meta['file']
        if file.parent.resolve()!=evidence.resolve():raise ValueError('Invalid evidence path.')
        if hashlib.sha256(file.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Replay payload hash mismatch.')
        worlds=make_worlds(manifest['frozen_plan']['configs']);env=OrganizationEnsemble(worlds)
        class Tape:
            def __init__(self,stream):self.stream=stream;self.hashes=[];self.step=0
            def decide(self,state,questions):
                row=json.loads(next(self.stream));self.step+=1
                if row['round']!=self.step or digest([state,questions])!=row['input_sha256']:
                    raise AssertionError('Regenerated local inputs differ.')
                self.hashes.append(row['metrics_sha256']);return row['probabilities']
            def usage(self):return {'actual_model_api_calls':0,'engine':'offline-recorded-probabilities'}
        with gzip.open(file,'rt',encoding='utf-8') as stream:
            tape=Tape(stream);result=run_simulation(env,tape,rounds=meta['periods'],seed=manifest['sampling_seed'])
            if next(stream,None) is not None:raise AssertionError('Unconsumed evidence rows.')
        if result['decisions']!=meta['decisions'] or [digest(m) for m in result['metrics']]!=tape.hashes:
            raise AssertionError('Replayed trajectory differs.')
        if {wid:digest(w.snapshot()) for wid,w in worlds.items()}!=meta['final_states_sha256']:
            raise AssertionError('Replayed final individual state differs.')
        output[engine]=dict(periods=meta['periods'],decisions=result['decisions'],all_inputs_exact=True,
            all_metrics_exact=True,full_final_states_exact=True,actual_model_api_calls=0)
        print(json.dumps({engine:output[engine]}),flush=True)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',default='docs/organizational_conventions/results')
    parser.add_argument('--engine',choices=['jev','uniform','history','notice','all'],default='all')
    args=parser.parse_args();replay(Path(args.evidence),None if args.engine=='all' else {args.engine})
