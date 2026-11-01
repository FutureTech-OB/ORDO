"""Export local synthetic experiment records for offline review; no API calls."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path('docs/appendix_ordo_v2_evidence')
SECRET=re.compile(rb'sk-or-v1-[A-Za-z0-9]{12,}|apikey_[A-Za-z0-9_]{20,}|"Authorization"\s*:')


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    rows=[]
    def export(source,destination,compressed=False):
        source=Path(source);out=ROOT/destination;out.parent.mkdir(parents=True,exist_ok=True)
        raw_hash=hashlib.sha256();size=0
        with source.open('rb') as stream:
            with (gzip.open(out,'wb') if compressed else out.open('wb')) as target:
                for line in stream:
                    if SECRET.search(line):raise ValueError('Credential-like field in export: '+str(source))
                    raw_hash.update(line);size+=len(line);target.write(line)
        rows.append(dict(path=destination,source=source.as_posix(),bytes=out.stat().st_size,
            source_bytes=size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
            uncompressed_sha256=raw_hash.hexdigest(),compression='gzip' if compressed else None))
    naming=Path('runs/behavior-jev-20261029')
    for name in ['plan-before-calls.json','verification.json','naming-jev-worlds.json','naming-uniform-worlds.json']:
        export(naming/name,'naming/'+name)
    for kind in ['naming-jev','naming-uniform']:
        for name in ['events.jsonl','result.json']:
            export(naming/kind/name,'naming/'+kind+'-'+name+'.gz',True)
    export(naming/'calls/openrouter_calls.jsonl','naming/shared-provider-calls.jsonl.gz',True)
    for label,source in [('majority','runs/llm-original-sa-demarzo-20261030'),('games','runs/llm-nhb-sampled-20261030')]:
        run=Path(source);report=json.loads((run/'verification.json').read_text())
        if report['status']!='complete':raise ValueError('Expected complete source run.')
        for name in ['plan-before-calls.json','verification.json','analysis.json']:
            export(run/name,label+'/'+name)
        for name in ['events.jsonl','result.json']:
            export(run/f"live-{report['attempt']}"/name,label+'/'+name+'.gz',True)
        for file in sorted(run.glob('calls-*/openrouter_calls.jsonl')):
            export(file,label+'/'+file.parent.name+'-'+file.name+'.gz',True)
        if label=='games':export(run/'source_trace.json',label+'/source_trace.json')
    partial=Path('runs/nc-polarization-hybrid-20261030')
    for name in ['plan-before-calls.json','verification.json','progress.json']:
        export(partial/name,'polarization-partial/'+name)
    manifest=dict(schema='ordo-review-v2',snapshot_date='2026-10-30',files=rows,
        completed_cases=['naming','majority','games'],partial_case='polarization-partial',
        naming_billing_scope='shared-provider-calls also contains the older opinion pilot; no naming-only cost is inferred',
        interpretation='Original-event replay checks saved inputs and outcomes, not independent fresh-model reproducibility.',
        credentials_exported=False,model_api_calls=0)
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (ROOT/'README.md').write_text('# Offline review evidence\n\n'
        'Exported synthetic experiment records for the v2 technical appendix. '
        'The manifest lists hashes of compressed and original bytes. No API credentials are included.\n\n'
        '`naming/` includes a shared provider journal also containing the older opinion pilot; '
        'its provider cost must not be assigned to the naming experiment alone. '
        '`majority/` is the newer twenty-world condition. `games/` is the raw-probability sampling run. '
        '`polarization-partial/` records an interrupted run and is not a completed forty-epoch result.\n\n'
        'From the repository root, run `python tools/replay_ordo_v2_review.py` to verify all exported bytes '
        'and replay the three completed cases without model API calls. The NHB replay requires the pinned '
        'public author source cache; see the appendix for its free download command.\n',encoding='utf-8')
    print(json.dumps(dict(files=len(rows),compressed_and_plain_bytes=sum(r['bytes'] for r in rows),output=ROOT.as_posix())))


if __name__=='__main__':main()
