"""Bounded public-source downloads and data-only archive parsing. No API keys."""
import hashlib
import io
import json
import math
from pathlib import Path
import pickle
import urllib.request
import zipfile


NORM_REPO='https://github.com/Ariel-Flint-Ashery/AI-norms'
OPINION_REPO='https://github.com/giordano-demarzo/LLMs-Opinion-Dynamics'
CURVES={
 'magnetization_0_50_0.2_0.0_claude-3-haiku-20240307.txt':'03fb6299f1c50445f7fffb2efb50c391973b2d36',
 'magnetization_0_50_0.2_0.0_claude-3-opus-20240229.txt':'501d735756655947c2fc5f6aee465c3891d4e412',
 'magnetization_0_50_0.2_0.0_gpt-3.5-turbo-1106.txt':'6d5fb2a27ec73583293e93a3b34b20103db10e94',
 'magnetization_0_50_0.2_0.0_gpt-4-turbo-2024-04-09.txt':'9f68683135301b30b5e009646feb6fed80c3ee7f',
 'magnetization_9_50_0.2_0.0_meta-llama-3-70b-instruct.txt':'9febeb704e812e124efbda52d4f187684374f496'}
TABLES={
 'transition_prob_50_0.2_claude-2.0_k_z.txt':'e0b3a3f82fa3bdc418dd5cf4b351743e85059a6b',
 'transition_prob_50_0.2_claude-3-5-sonnet-20240620_k_z.txt':'7551c1538de857f6e8ad55a3a3de7cabf1c8381c',
 'transition_prob_50_0.2_claude-3-haiku-20240307_k_z.txt':'0733efedc8a638a60b25c658a529be87ae9b8b82',
 'transition_prob_50_0.2_claude-3-opus-20240229.txt':'03f145376bb5e8bf7b5c6763d662c630326e1439',
 'transition_prob_50_0.2_claude-3-sonnet-20240229.txt':'b4147a775aee8b0e7e80e71b80959d5757b75075',
 'transition_prob_50_0.2_gpt-3.5-turbo-1106_k_z.txt':'30c799be39715ece1fd4301651b46fd2224eab5b',
 'transition_prob_50_0.2_gpt-4-0613.txt':'d1688739984d06ebdfbd0c2c400c009f9bd4a0bc',
 'transition_prob_50_0.2_gpt-4-turbo-2024-04-09.txt':'f5c2960d3d437a1a9ae49691aaf61a3f90e432cf',
 'transition_prob_50_0.2_gpt-4o-2024-05-13_k_z.txt':'f9e4d5b00ca2b0090a21aff79842b308889a9b25',
 'transition_prob_50_0.2_meta-llama-3-70b-instruct_k_z.txt':'3434803c445702039ce3e18a732adba1951a93d7'}
ARCHIVES={
 'spontaneous_W10':'claude_data/claude_converged_baseline_Q_M_X_Y_F_J_P_R_C_D_-50_100_5mem_complete_24ps_0.5tmp.pkl',
 'minority_4_Q_to_M':'claude_data/claude_swap_0_4cmtd_Q_M_-50_100_5mem_complete_24ps_0.5tmp.pkl',
 'minority_5_Q_to_M':'claude_data/claude_swap_0_5cmtd_Q_M_-50_100_5mem_complete_24ps_0.5tmp.pkl',
 'individual_W10':'claude_data/claude_no_memory_bias_test_QMXYFJPRCD_0mem.pkl'}


def git_blob_sha(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def public_file(root,name,url,expected,download=False):
    path=Path(root)/name
    if path.exists(): raw=path.read_bytes()
    elif download:
        with urllib.request.urlopen(url,timeout=30) as response: raw=response.read(3_000_001)
        if len(raw)>3_000_000: raise ValueError('Unexpectedly large source file.')
        if git_blob_sha(raw)!=expected: raise ValueError('Upstream bytes changed; inspect and update the declared version.')
        path.write_bytes(raw)
    else: raise FileNotFoundError(f'Fetch public sources explicitly with --download: {name}')
    if git_blob_sha(raw)!=expected: raise ValueError('Cached source hash differs from pinned upstream bytes.')
    return raw,dict(file=name,url=url,git_blob_sha=expected,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


class DataOnlyUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        raise pickle.UnpicklingError('Archive object construction is disabled.')
    def persistent_load(self,pid):
        raise pickle.UnpicklingError('Persistent archive references are disabled.')


def archive_data(raw,member):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.getinfo(member).file_size>20_000_000: raise ValueError('Archive member too large.')
        return DataOnlyUnpickler(io.BytesIO(archive.read(member))).load()


def numeric_rows(raw,columns=2):
    rows=[]
    for line in raw.decode('utf-8-sig').splitlines():
        if not line.strip(): continue
        parts=line.split(',')
        allowed=(columns,) if isinstance(columns,int) else columns
        if len(parts) not in allowed: raise ValueError(f'Expected column counts {allowed}.')
        values=[float(x) for x in parts]
        if not all(math.isfinite(x) for x in values): raise ValueError('Nonfinite source values.')
        rows.append(values)
    if not rows: raise ValueError('Empty source table.')
    return rows


def split_opinion_trace(raw,population=50):
    """Keep appended trial restarts separate; do not invent latent agent choices."""
    segments=[]
    for step,m in numeric_rows(raw):
        if step!=int(step) or step<0 or abs(m)>1+1e-9: raise ValueError('Invalid macro trajectory.')
        if abs((m+1)*population/2-round((m+1)*population/2))>1e-7:
            raise ValueError('Opinion count lies off the integer population lattice.')
        if not segments or step<=segments[-1][-1][0]: segments.append([])
        if segments[-1]:
            previous=segments[-1][-1]
            if step!=previous[0]+1: raise ValueError('Missing updates inside a source segment.')
            if abs(m-previous[1])>2/population+1e-7: raise ValueError('Not a single-agent update.')
        segments[-1].append([int(step),m])
    return segments


def load_sources(root,download=False):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    raw,meta=public_file(root,'claude_data.zip',
        'https://raw.githubusercontent.com/Ariel-Flint-Ashery/AI-norms/main/data/claude_data.zip',
        'c4ae4e90ba79a869ef100adf88a37e41df13c52d',download)
    result=dict(norms={key:archive_data(raw,path) for key,path in ARCHIVES.items()},curves={},tables={},sources=[meta])
    for name,sha in CURVES.items():
        data,meta=public_file(root,name,'https://raw.githubusercontent.com/giordano-demarzo/LLMs-Opinion-Dynamics/master/fully_connected_50/'+name,sha,download)
        result['curves'][name]=split_opinion_trace(data); result['sources'].append(meta)
    for name,sha in TABLES.items():
        data,meta=public_file(root,name,'https://raw.githubusercontent.com/giordano-demarzo/LLMs-Opinion-Dynamics/master/transition_prob_various_models_kz/50_kz/'+name,sha,download)
        rows=numeric_rows(data,columns=(2,4))
        # Upstream schemas: (m, k share) or (m, k count, z count, k share).
        for row in rows:
            m,p=row[0],row[-1]
            if abs(m)>1 or not 0<=p<=1:
                raise ValueError('Invalid adoption table.')
            if len(row)==4:
                k,z=row[1:3]
                if min(k,z)<0 or k!=int(k) or z!=int(z) or k+z<=0:
                    raise ValueError('Invalid adoption counts.')
            # Preserve reported shares verbatim. Some files count fewer than
            # the intended trials; report that discrepancy instead of renormalizing.
        result['tables'][name]=rows; result['sources'].append(meta)
    (root/'source_manifest.json').write_text(json.dumps(result['sources'],indent=2)+'\n',encoding='utf-8')
    return result
