"""Pinned research-source cache and native reference, never a paid API route."""
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

REPO='https://github.com/DaniMuzi/SocialMedia'
COMMIT='e451640f7f86dc32f293aa465f8d899d359db1dc'
FILES={
    'models_algorithm.c':'1dab0dedfc5500ef2679213dc56ac6a8b834173c',
    'models_algorithm.h':'c1a08aafbb7b7296212558db1d32a8fa042d6377',
    'mt19937-64.c':'12a855cb89e030eb3acbfa89c9cb22d17ec4c455',
    'mt64.h':'0a1873c74d4a17155c3ddbb71d067af5c2dad5f5',
    'my_sort.c':'9893429854424bceebf5dec1ba14f24251069b51',
    'my_sort.h':'4b30b71c1d7d4101a07a845b7caaf9eb224a2981'}


def load_sources(cache,download=False):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);manifest=[]
    for name,sha in FILES.items():
        file=cache/name;url=f'https://raw.githubusercontent.com/DaniMuzi/SocialMedia/{COMMIT}/data_vs_models/code/{name}'
        if not file.exists():
            if not download:raise FileNotFoundError('Fetch pinned research sources using --download.')
            with urllib.request.urlopen(url,timeout=40) as response:raw=response.read(512001)
            if len(raw)>512000:raise ValueError('Research source exceeded bounded download size.')
            if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Source changed.')
            file.write_bytes(raw)
        raw=file.read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Cached source changed.')
        manifest.append(dict(file=name,url=url,git_blob_sha=sha,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    return manifest


WRAPPER=r'''
#include <stdlib.h>
#include "models_algorithm.h"
#include "my_sort.h"
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
/* Instrument the author's find_seed/next_shell functions without changing them.
   Inputs are supplied Gaussian random fields, so RNG implementations need not match. */
EXPORT int record_rfim(int N,const double *inputs,int *shells,int *avalanche_ids,double *external_fields,int *remaining) {
    double *fields=(double*)malloc((N+1)*sizeof(double));
    double E=-1.0,H,working;int j,k=0,ava=0,s,S;
    if(!fields)return -1;
    for(j=1;j<=N;j++)fields[j]=inputs[j-1];
    q_sort_double(fields,1,N);fields[0]=N;
    while(fields[0]>0) {
        ava++;H=find_seed(fields,E);working=E+2.0/(double)N;S=1;
        shells[k]=1;avalanche_ids[k]=ava;external_fields[k]=H;remaining[k++]=(int)fields[0];
        do {
            s=next_shell(fields,H,working);S+=s;
            shells[k]=s;avalanche_ids[k]=ava;external_fields[k]=H;remaining[k++]=(int)fields[0];
            working+=2.0*s/(double)N;
        } while(s>0);
        E+=2.0*(double)S/(double)N;
    }
    free(fields);return k;
}
'''


def build_reference(cache,force=False):
    cache=Path(cache).resolve();is_windows=__import__('os').name=='nt'
    target=cache/('author_rfim.dll' if is_windows else 'author_rfim.so')
    wrapper=cache/'reference_wrapper.c'
    if wrapper.exists() and wrapper.read_text(encoding='utf-8')!=WRAPPER:force=True
    wrapper.write_text(WRAPPER,encoding='utf-8')
    # The upstream include is POSIX-only and unused by its numerical kernel.
    # This empty compatibility header does not change the downloaded source.
    (cache/'unistd.h').write_text('/* Unused POSIX include compatibility for Windows. */\n',encoding='utf-8')
    if not target.exists() or force:
        if is_windows:
            vcvars=Path('C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Auxiliary/Build/vcvars64.bat')
            if not vcvars.exists():raise FileNotFoundError('Install a C compiler; the cookbook accepts GCC/Clang on Unix or VS BuildTools on Windows.')
            script=cache/'compile_reference.cmd'
            script.write_text(f'@echo off\ncall "{vcvars}" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /TC /O2 /D_USE_MATH_DEFINES /LD /I. reference_wrapper.c models_algorithm.c my_sort.c mt19937-64.c /link /OUT:author_rfim.dll\n',encoding='utf-8')
            result=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=cache,capture_output=True,text=True)
        else:
            compiler=shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
            if not compiler:raise FileNotFoundError('A C compiler is required for the independent author reference.')
            result=subprocess.run([compiler,'-O2','-shared','-fPIC','-D_DEFAULT_SOURCE','-I.',
                'reference_wrapper.c','models_algorithm.c','my_sort.c','mt19937-64.c','-lm','-o',str(target)],cwd=cache,capture_output=True,text=True)
        (cache/'compile.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError('Native reference build failed; inspect the cache compile.log.')
    return target


def author_reference(fields,library):
    n=len(fields);capacity=2*n
    values=(ctypes.c_double*n)(*fields);shells=(ctypes.c_int*capacity)();avalanches=(ctypes.c_int*capacity)()
    H=(ctypes.c_double*capacity)();remaining=(ctypes.c_int*capacity)()
    lib=ctypes.CDLL(str(Path(library).resolve()));f=lib.record_rfim
    f.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int)]
    f.restype=ctypes.c_int;k=f(n,values,shells,avalanches,H,remaining)
    if not 0<k<=capacity:raise RuntimeError('Unexpected native event count.')
    return [dict(shell_size=shells[i],avalanche=avalanches[i],field=H[i],remaining=remaining[i]) for i in range(k)]
