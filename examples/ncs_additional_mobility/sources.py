"""Bounded, SHA-pinned public downloads for the GPL-3.0 PedNav component."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error
import time

COMMIT='8aa7bb147dcd9e7b3b3bb3183cae6b583cca4980'
REPO='https://github.com/cbongiorno/pednav'
DOI='10.1038/s43588-021-00130-y'
FILES={
    'pednav/main.py':('73ed226629782cd606a9411af3492cee74e801da',2499),
    'data/graph_clusters_30m_bos.pk':('c6010f95cfd590daf261882f177c93e614d1f241',49774096),
    'data/Human_Paths_bos.pk':('2fae307921b121778338bc885b4e662a106e2ac0',17949),
    'LICENSE':('f288702d2fa16d3cdf0035b15a9fcbc552cd88e7',35149)}
DEFAULT=Path('.buildtmp/ncs-pednav-sources')


def load_sources(cache=DEFAULT,download=False):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);rows=[]
    for name,(sha,size) in FILES.items():
        file=cache/name;url=f'https://raw.githubusercontent.com/cbongiorno/pednav/{COMMIT}/{name}'
        if not file.exists():
            if not download:raise FileNotFoundError('Use --download once to fetch the pinned public PedNav sources.')
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=45) as response:raw=response.read(size+1)
                    break
                except (urllib.error.URLError,TimeoutError,ConnectionError):
                    if attempt==2:raise
                    time.sleep(2**attempt)
            if len(raw)!=size:raise ValueError('Unexpected source size: '+name)
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if blob!=sha:raise ValueError('Unexpected source hash: '+name)
            file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
        raw=file.read_bytes()
        if len(raw)!=size or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:
            raise ValueError('Pinned source changed: '+name)
        rows.append(dict(file=name,url=url,git_blob_sha=sha,sha256=hashlib.sha256(raw).hexdigest(),bytes=size))
    manifest=dict(doi=DOI,repository=REPO,commit=COMMIT,code_license='GPL-3.0',files=rows)
    (cache/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=DEFAULT);p.add_argument('--download',action='store_true')
    a=p.parse_args();print(json.dumps(load_sources(a.cache,a.download),indent=2))
