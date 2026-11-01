"""Read the exact public capsule configuration; never substitute it for private MIT data."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from examples.ncs_colocation.sources import checkout,load_pickle,author_class,COMMIT,URL


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def graph_record(graph):
    return dict(nodes=list(graph.nodes),edges=[list(e) for e in graph.edges])


def memory_record(memory):
    return [[list(e),v] for e,v in memory.items()]


def load(cache='.buildtmp/ncs-colocation-source',download=False):
    root=checkout(cache,download);code=root/'code'
    notebook=json.loads((code/'SimulationsSubmission.ipynb').read_text(encoding='utf-8'))
    dist=load_pickle(code/'dist_dict_demo.p');dates=load_pickle(code/'dates_fall2021.p')
    graphs=load_pickle(code/'undir_semiactive_demo.p')
    weekday_inds=[i for i,date in enumerate(dates) if 0<date.weekday()<6]
    weekday_dates=[dates[i] for i in weekday_inds]
    weekday_graphs=[g for i,g in enumerate(graphs) if i in weekday_inds]
    all_edges=set()
    for graph in weekday_graphs:
        all_edges=all_edges.union(set(tuple(sorted(e)) for e in graph.edges))
    # Match the notebook's set-to-dict construction; no population/candidate reduction.
    memory={tuple(sorted(e)):[] for e in all_edges}
    for i,graph in enumerate(weekday_graphs[26:36]):
        for edge in graph.edges:memory[tuple(sorted(edge))].append(i)
    assignment=ast.parse(''.join(notebook['cells'][11]['source'])).body[0]
    def numeric(node):
        if isinstance(node,ast.Constant):return node.value
        if isinstance(node,ast.Dict):return {numeric(k):numeric(v) for k,v in zip(node.keys,node.values)}
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div):return numeric(node.left)/numeric(node.right)
        raise ValueError('Unexpected expression in pinned numeric author parameters.')
    parameters=numeric(assignment.value)
    assert len(weekday_dates)==477 and len(all_edges)==1577
    files=['code/SimulationsSubmission.ipynb','code/dist_dict_demo.p','code/dates_fall2021.p',
           'code/undir_semiactive_demo.p','code/LICENSE']
    metadata=dict(paper_doi='10.1038/s43588-022-00296-z',source_doi='10.24433/CO.5754680.v1',
        source_url=URL,commit=COMMIT,scope='Complete author public-capsule simulation configuration; private full MIT population unavailable.',
        public_graph_unique_nodes=len({n for g in graphs for n in g}),
        public_distance_unique_ids=len({n for e in dist for n in e}),
        candidate_edges=len(all_edges),candidate_endpoints=len({n for e in all_edges for n in e}),
        date_count=len(dates),filtered_dates=len(weekday_dates),graph_count=len(graphs),filtered_graph_count=len(weekday_graphs),
        weekday_rule='0 < datetime.weekday() < 6, retained exactly (Tuesday through Saturday)',
        initialization='all historical weekday edges; memory populated from weekday_graphs[26:36], indexed 0..9',
        author_parameters=parameters,source_hashes={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},
        phases=[dict(id='shared_colocated_prefix',start=10,end=62,days=52,remote=False),
                dict(id='remote',start=62,end=439,days=377,remote=True),
                dict(id='return',start=439,end=len(weekday_dates),days=len(weekday_dates)-439,remote=False),
                dict(id='nochange_counterfactual',start=62,end=len(weekday_dates),days=len(weekday_dates)-62,remote=False)],
        actual_boundary_dates={str(i):weekday_dates[i].isoformat() for i in [10,61,62,438,439,476]},
        original_seed='Notebook calls random.seed(42), but its sampler uses unseeded np.random. Exact published initial NumPy state is not archived.',
        repetitions='One intervention path and one nochange counterfactual sharing the prefix; no seed replication loop in the public notebook.')
    return root,notebook,dist,weekday_dates,memory,parameters,metadata
