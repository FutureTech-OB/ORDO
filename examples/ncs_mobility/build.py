"""Fetch pinned public MIT source and build a bounded native-kernel bridge."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

COMMIT='21be090028a0b090c6d32675b73ef821893dfaf9'
REPO='https://github.com/tsinghua-fib-lab/Collective-Mobility-Model'
FILES={'main.cpp':'306e9b8dd06640920f098e3a72ef8456ab144c2b',
       'drand48.h':'46d86e880af91f6a7ba7abad2151d484969342b9',
       'LICENSE':'6c603710c5d0bc0dae1b362812b3cbfacbe46867'}
DEFAULT=Path('.buildtmp/ncs-mobility-native')


def source(root,download=False):
    root.mkdir(parents=True,exist_ok=True);manifest={}
    for name,sha in FILES.items():
        path=root/name;url=f'https://raw.githubusercontent.com/tsinghua-fib-lab/Collective-Mobility-Model/{COMMIT}/{name}'
        if not path.exists():
            if not download:raise FileNotFoundError('Use --download once to fetch the pinned public source.')
            with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(1000001)
            if len(raw)>1000000:raise ValueError('Source exceeds declared size bound.')
            actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if actual!=sha:raise ValueError('Unexpected source bytes.')
            path.write_bytes(raw)
        raw=path.read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:
            raise ValueError('Source hash mismatch.')
        manifest[name]=dict(url=url,git_blob_sha=sha,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    (root/'source_manifest.json').write_text(json.dumps(dict(repository=REPO,commit=COMMIT,files=manifest),indent=2)+'\n',encoding='utf-8')
    return manifest


def build(root=DEFAULT,download=False):
    root=Path(root).resolve();source(root,download)
    original=(root/'main.cpp').read_bytes().decode('gb18030',errors='replace').replace('\r\n','\n')
    prefix=original[:original.index('class t_sta')]
    update=original[original.index('void update(int t)'):original.index('int run(const char* dirname)')]
    prefix=prefix.replace('#include <hash_map>','// Unused deprecated <hash_map> omitted by bridge.')
    old='while((freq_temp>this->frequency[index_temp-1])&&index_temp>0)'
    if prefix.count(old)!=1:raise ValueError('SortedArray source changed.')
    prefix=prefix.replace(old,'while(index_temp>0&&(freq_temp>this->frequency[index_temp-1]))')
    marker='public:\n\tt_user()'
    if marker not in prefix:raise ValueError('Unexpected t_user declaration.')
    getters='''public:
    int bridge_position() const { return pos; }
    int bridge_visited() const { return visited_num; }
    long bridge_times() const { return times; }
    unsigned long long bridge_seed() const { return (unsigned long long)seed_pre; }
    void bridge_entry(int i,int &label,int &frequency) { loc_freq->select(i,label,frequency); }
    void bridge_cleanup() { delete loc_freq; loc_freq=nullptr; }

\tt_user()'''
    prefix=prefix.replace(marker,getters)
    tail=Path(__file__).with_name('bridge_tail.cpp').read_text(encoding='utf-8')
    generated=prefix+'\n'+update+'\n'+tail
    (root/'bridge.cpp').write_text(generated,encoding='utf-8')
    vswhere=Path('C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe')
    if not vswhere.exists():raise RuntimeError('This native cookbook currently requires Windows MSVC/PPL Build Tools.')
    vs=subprocess.check_output([str(vswhere),'-latest','-products','*','-property','installationPath'],text=True).strip()
    vcvars=Path(vs)/'VC/Auxiliary/Build/vcvars64.bat'
    if not vcvars.exists():raise RuntimeError('MSVC x64 build environment unavailable.')
    commands=[f'call "{vcvars}"',
        'cl /nologo /EHsc /O2 /utf-8 /D_CRT_SECURE_NO_WARNINGS /LD bridge.cpp /Fe:cmm_bridge.dll /link /NOLOGO',
        'if errorlevel 1 exit /b %errorlevel%',
        'cl /nologo /EHsc /O2 /utf-8 /D_CRT_SECURE_NO_WARNINGS /DBRIDGE_EXE bridge.cpp /Fe:cmm_reference.exe /link /NOLOGO',
        'exit /b %errorlevel%']
    script=root/'compile.cmd';script.write_text('\n'.join(commands)+'\n',encoding='utf-8')
    result=subprocess.run(['cmd','/c',str(script)],cwd=root,capture_output=True,text=True,errors='replace')
    (root/'compile.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Native build failed; inspect '+str(root/'compile.log'))
    meta=dict(commit=COMMIT,source_sha256=hashlib.sha256((root/'main.cpp').read_bytes()).hexdigest(),
        generated_sha256=hashlib.sha256((root/'bridge.cpp').read_bytes()).hexdigest(),
        patches=['Use source prefix through t_user plus unchanged update function; omit original main/run/output routines.',
        'Omit unused deprecated hash_map include.',
        'Check index_temp>0 before frequency[index_temp-1] in SortedArray.add to avoid out-of-bounds read.',
        'Add read-only state getters and explicit loc_freq cleanup.',
        'Use new[]/delete[] in bridge initialization; deterministic explicit seeds instead of time().',
        'Run agents serially under the unchanged frozen-population period update, retaining per-agent RNG.'],
        platform='Windows x64 MSVC/PPL',algorithms='Author t_user exploration/return, SortedArray, AliasTable and update; source quirks retained except bounds guard.')
    for name in ('cmm_bridge.dll','cmm_reference.exe'):meta[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    (root/'build_manifest.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2));return root


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--download',action='store_true');p.add_argument('--root',type=Path,default=DEFAULT)
    a=p.parse_args();build(a.root,a.download)
