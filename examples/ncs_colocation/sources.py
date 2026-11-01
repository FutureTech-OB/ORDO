"""Load the MIT-licensed published Code Ocean simulation without notebook execution."""
import ast
import builtins
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import pickle
import subprocess

import networkx as nx
import numpy as np

URL = 'https://git.codeocean.com/capsule-8904315.git'
COMMIT = 'cbb02661a19d73136dc585645f6f2422054b15a7'
DEFAULT_CACHE = '.buildtmp/ncs-colocation-source'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checkout(cache=DEFAULT_CACHE, download=False):
    root = Path(cache)
    if not root.exists():
        if not download:
            raise FileNotFoundError('Use --download to obtain the public author capsule.')
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--depth', '1', '--branch', 'v1.0', URL, str(root)], check=True)
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if head != COMMIT:
        raise ValueError('Author capsule commit differs from the pinned release.')
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True).strip():
        raise ValueError('Tracked upstream files have local changes; use a clean author checkout.')
    return root


class RestrictedUnpickler(pickle.Unpickler):
    """Only the public capsule's graph/date containers are permitted."""
    def find_class(self, module, name):
        allowed = {('datetime', 'datetime'): datetime,
                   ('networkx.classes.graph', 'Graph'): nx.Graph,
                   ('networkx.classes.reportviews', 'NodeView'): nx.classes.reportviews.NodeView,
                   ('builtins', 'dict'): dict}
        if (module, name) not in allowed:
            raise pickle.UnpicklingError(f'Unexpected global {module}.{name}')
        return allowed[module, name]


def load_pickle(path):
    return RestrictedUnpickler(io.BytesIO(Path(path).read_bytes())).load()


def dataset(root, population):
    """Induce a declared public-demo subset; preserve author weekday/init conventions."""
    code = Path(root)/'code'
    distances = load_pickle(code/'dist_dict_demo.p')
    dates = load_pickle(code/'dates_fall2021.p')
    graphs = load_pickle(code/'undir_semiactive_demo.p')
    nodes = sorted({v for edge in distances for v in edge})[:population]
    keep = set(nodes)
    distances = {e: v for e, v in distances.items() if set(e) <= keep}
    indices = [i for i, d in enumerate(dates) if 0 < d.weekday() < 6]
    weekday_dates = [dates[i] for i in indices]
    # This exact (Tuesday--Saturday) convention is in the author notebook.
    weekday_graphs = [g.subgraph(nodes).copy() for i, g in enumerate(graphs) if i in indices]
    all_edges = set()
    for g in weekday_graphs:
        all_edges.update(tuple(sorted(e)) for e in g.edges)
    # Stabilize set iteration across Python processes, and document the change.
    memory = {edge: [] for edge in sorted(all_edges)}
    for i, g in enumerate(weekday_graphs[26:36]):
        for edge in g.edges:
            memory[tuple(sorted(edge))].append(i)
    if len(memory) < 90:
        raise ValueError('Subset has too few available ties for the native 50+20 daily draws.')
    return nodes, distances, weekday_dates, memory


class DailyYield(ast.NodeTransformer):
    """Insert one observation yield after each original complete-day transition."""
    def __init__(self):
        self.insertions = 0

    def visit_FunctionDef(self, node):
        if node.name != 'transform':
            return node
        for statement in node.body:
            if (isinstance(statement, ast.For) and isinstance(statement.target, ast.Tuple)
                    and [getattr(x, 'id', None) for x in statement.target.elts] == ['day_ind', 'day']):
                statement.body.append(ast.Expr(ast.Yield(ast.Name('G', ast.Load()))))
                self.insertions += 1
        return node


def author_class(root, distances, dates, daily=False):
    """Extract author helper/class cells; no unrelated analyses/imports are executed."""
    notebook = json.loads((Path(root)/'code/SimulationsSubmission.ipynb').read_text(encoding='utf-8'))
    helper = ''.join(notebook['cells'][1]['source'])
    source = ''.join(notebook['cells'][8]['source'])
    tree = ast.parse(source)
    if daily:
        patch = DailyYield()
        tree = patch.visit(tree)
        if patch.insertions != 1:
            raise ValueError('The pinned author day loop no longer matches.')
        ast.fix_missing_locations(tree)
    namespace = dict(np=np, nx=nx, deepcopy=deepcopy, merge=None,
                     BaseEstimator=type('BaseEstimator', (), {}),
                     TransformerMixin=type('TransformerMixin', (), {}),
                     trange=range, dist_dict=distances, weekday_dates=dates)
    exec(compile(ast.parse(helper), '<author-helper>', 'exec'), namespace)
    exec(compile(tree, '<author-simulation>', 'exec'), namespace)
    return namespace['graph_generator'], hashlib.sha256(ast.dump(tree).encode()).hexdigest()


PARAMETERS = dict(period=5, periodicity_weight=80000, new_connection_weight=2000,
                  old_connection_weight=1, distance_weight=0, distance_add_weight=0,
                  dpt_weight=90000, closure_weight=200000, per_interaction=1/1.5,
                  new_interaction=2, old_interaction=1, closure_interaction=1/1.5,
                  dpt_interaction=1/1.1, normal_scale=3, verbose=False)
