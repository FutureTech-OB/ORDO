import argparse
import ast
import hashlib
import json
from pathlib import Path
import random
import urllib.request

COMMIT='224a605a21127cac69763f990e077f7b05abd422'
ROOT=Path('.buildtmp/nhb-repeatedgames')
SCRIPT='pd/tft/pd_base_gpt4_tfts_query.py'
CSV='pd/tft/data/pd_base_gpt4_tfts.csv'
FILES={SCRIPT:('63badbcf8288b6cc7326a4d32866d3655c7a3253',7833),CSV:('a25bf44cac213bb4ea2d19d23aad8f9a7341d201',44713),'LICENSE.md':('108cffb7c9fcd38dadc419f4c18e4e3e0afb4407',1067)}
PLAYERS=('act_gpt4','act_tft','act_tftt','act_stft','act_rtft','act_htft','act_np10','act_np20')


def sources(root=ROOT,download=False):
    root=Path(root);rows=[]
    for name,(sha,size) in FILES.items():
        p=root/name;url=f'https://raw.githubusercontent.com/eliaka/repeatedgames/{COMMIT}/{name}'
        if not p.exists():
            if not download:raise FileNotFoundError('Obtain pinned public sources with --download.')
            with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(size+1)
            if len(raw)!=size:raise ValueError('Unexpected source size.')
            if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Wrong public source.')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        raw=p.read_bytes()
        if len(raw)!=size or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Pinned source differs: '+name)
        rows.append(dict(path=name,url=url,git_blob_sha=sha,sha256=hashlib.sha256(raw).hexdigest(),bytes=size))
    return dict(commit=COMMIT,license='MIT,copyright2024ElifAkata',files=rows)


def author_namespace(seed,root=ROOT):
    sources(root);tree=ast.parse((Path(root)/SCRIPT).read_text(encoding='utf-8'))
    names=set(PLAYERS[1:])|{'calculate_points'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    nodes += [n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('num_interactions','question')]
    if len(nodes)!=10:raise ValueError('Pinned protocol AST differs.')
    namespace={'random':random.Random(seed)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned-author-no-api>','exec'),namespace)
    return namespace,tree


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');a=p.parse_args()
    print(json.dumps(sources(download=a.download),indent=2))
