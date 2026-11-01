"""Pinned GPL author modules, loaded separately from this project's source tree."""
import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import urllib.request

COMMIT='93d4984cac10171acb14ccdae5bc68a9e4d76e20'
REPO='https://github.com/charleywu/minecraftforaging'
FILES={
    'simulations/simulation.py':'e1ad06cae6bc931e8ef5be6f6c48b89385c4afd6',
    'simulations/task.py':'35ce19a0e511bdc371dd1e75583c716c61e1be42',
    'simulations/spatial_gp.py':'f7521e698c47434c9ef72ef4910f791a39c6808b',
    'simulations/runSimulations.py':'56eec9e9b659a8ca9f1783e8d789ce76a8ea32dc',
    'environments/smooth.1.csv':'a1b44f6a14ca8177314ddf230139cd1137a01302',
    'environments/random.1.csv':'5574b4e57843427a6ff06b58d9d2e1fdb933e9e0',
    'LICENSE':'f288702d2fa16d3cdf0035b15a9fcbc552cd88e7'}


def load_sources(cache,download=False):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);manifest=[]
    for path,sha in FILES.items():
        file=cache/Path(path).name;url=f'https://raw.githubusercontent.com/charleywu/minecraftforaging/{COMMIT}/{path}'
        if not file.exists():
            if not download:raise FileNotFoundError('Fetch pinned foraging sources using --download.')
            with urllib.request.urlopen(url,timeout=40) as response:raw=response.read(512001)
            if len(raw)>512000:raise ValueError('Research source exceeded bounded size.')
            if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Source changed.')
            file.write_bytes(raw)
        raw=file.read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Cached source changed.')
        manifest.append(dict(file=path,url=url,git_blob_sha=sha,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    return manifest


def load_author(cache):
    """Preserve original modules and inject exactly one cooperative yield boundary."""
    cache=Path(cache).resolve()
    extra=Path('.buildtmp/nc-social-deps')
    if extra.exists():sys.path.insert(0,str(extra.resolve()))
    loaded={};old={name:sys.modules.get(name) for name in ('task','spatial_gp')}
    try:
        for name in ('spatial_gp','task','simulation'):
            unique='_ordo_nc_foraging_'+name
            spec=importlib.util.spec_from_file_location(unique,cache/f'{name}.py');module=importlib.util.module_from_spec(spec)
            sys.modules[unique]=module;spec.loader.exec_module(module);loaded[name]=module
            if name in old:sys.modules[name]=module
    finally:
        for name,value in old.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value
    tree=ast.parse((cache/'simulation.py').read_text(encoding='utf-8'))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Simulation')
    run=copy.deepcopy(next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='run'))
    run.name='run_generator';count=0
    class PauseChoice(ast.NodeTransformer):
        def visit_Assign(self,node):
            nonlocal count
            value=node.value
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='sample_next_cell':
                if not isinstance(value.func.value,ast.Name) or value.func.value.id!='policy':raise ValueError('Unexpected source call.')
                names=['step','agent_i','agent_view','state','policy','rng']
                node.value=ast.Yield(value=ast.Tuple(elts=[ast.Name(id=n,ctx=ast.Load()) for n in names],ctx=ast.Load()));count+=1
            return node
    run=PauseChoice().visit(run)
    if count!=1:raise ValueError('Author choice boundary changed; inspect before adapting.')
    transformed=ast.fix_missing_locations(ast.Module(body=[run],type_ignores=[]))
    exec(compile(transformed,'<pinned-author-foraging-yield-boundary>','exec'),loaded['simulation'].__dict__)
    return loaded['task'],loaded['simulation'],dict(replaced_calls=count,
        transformed_ast_sha256=hashlib.sha256(ast.dump(transformed,include_attributes=False).encode()).hexdigest(),
        transformation='Replace goal_cell = policy.sample_next_cell(...) with yield(step, agent_i, agent_view, state, policy, rng); remaining author run AST unchanged.')
