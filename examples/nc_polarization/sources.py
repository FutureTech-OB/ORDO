"""Bounded, hash-pinned public downloads; no model API or credential access."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


def blob_sha(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def load_sources(root,download=False):
    manifest=json.loads(Path(__file__).with_name('source_manifest.json').read_text(encoding='utf-8'))
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    def get(row):
        path=root/row['path']
        if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Invalid source path.')
        if path.exists():raw=path.read_bytes()
        elif download:
            url='https://raw.githubusercontent.com/'+manifest['repo']+'/'+manifest['commit']+'/'+urllib.parse.quote(row['path'],safe='/')
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=45) as response:raw=response.read(row['size']+1)
                    break
                except (urllib.error.URLError,TimeoutError,ConnectionError):
                    if attempt==2:raise
                    time.sleep(2**attempt)
        else:raise FileNotFoundError('Use --download to fetch the declared public sources: '+str(path))
        if len(raw)!=row['size'] or blob_sha(raw)!=row['git_blob_sha']:raise ValueError('Source bytes do not match pinned Git blob: '+row['path'])
        if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return dict(row,sha256=hashlib.sha256(raw).hexdigest())
    with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(get,manifest['files']))
    return dict(manifest,files=rows)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',default='.buildtmp/nc-polarization-sources');p.add_argument('--download',action='store_true')
    a=p.parse_args();m=load_sources(a.cache,a.download)
    print(json.dumps(dict(files=len(m['files']),bytes=sum(r['size'] for r in m['files']),commit=m['commit'])))
