"""List and run declared free cookbook entries; never load API credentials."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
import time


def catalog():
    return json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8'))['entries']


def commands(entry,output,download=False):
    specs=[*entry.get('prepare',[]),dict(module=entry['module'],args=entry.get('args',[]),
        download_flag=entry.get('download_flag'),is_run=True)]
    result=[]
    for step in specs:
        if not step['module'].startswith('examples.'):raise ValueError('Only declared example modules can run.')
        command=[sys.executable,'-m',step['module'],*[s.replace('{output}',str(output)) for s in step.get('args',[])]]
        if step.get('is_run'):command+=['--output',str(output)]
        if download and step.get('download_flag'):command.append(step['download_flag'])
        result.append(command)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list',action='store_true');p.add_argument('--recipe',default='all')
    p.add_argument('--preview',action='store_true');p.add_argument('--download',action='store_true')
    p.add_argument('--output');a=p.parse_args();entries=catalog()
    if a.list:
        for e in entries:print(json.dumps({k:e[k] for k in ['id','title','kind','docs','scope']},ensure_ascii=False))
        return
    selected=entries if a.recipe=='all' else [e for e in entries if e['id']==a.recipe]
    if not selected:p.error('Unknown recipe; use --list.')
    if a.preview:
        for e in selected:print(json.dumps(dict(id=e['id'],commands=commands(e,Path(a.output or 'runs/SUITE')/e['id'],a.download),
            platforms=e.get('platforms',['any']),expected_model_api_calls=0),ensure_ascii=False))
        return
    if not a.output:p.error('--output is required for a new suite directory.')
    repo=Path(__file__).resolve().parents[2];root=Path(a.output).resolve();root.mkdir(parents=True,exist_ok=False)
    report=dict(status='running',python=platform.python_version(),actual_paid_api_calls=0,recipes=[],
        scope='Free/native/archive entries only. Fresh paid decision-model experiments use their dedicated opt-in commands.')
    def save():(root/'suite_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save();started=time.perf_counter()
    for entry in selected:
        row=dict(id=entry['id'],kind=entry['kind'],scope=entry['scope'],status='running')
        report['recipes'].append(row);save()
        if entry.get('platforms') and sys.platform not in entry['platforms']:
            row.update(status='unsupported_platform',platform=sys.platform);save();continue
        directory=root/entry['id'];row['commands']=commands(entry,directory,a.download)
        row_started=time.perf_counter()
        try:
            with (root/(entry['id']+'.log')).open('w',encoding='utf-8') as stream:
                for command in row['commands']:
                    result=subprocess.run(command,cwd=repo,stdout=stream,stderr=subprocess.STDOUT,encoding='utf-8')
                    if result.returncode:raise RuntimeError('Cookbook exited with code '+str(result.returncode))
            row.update(status='complete',output=directory.relative_to(root).as_posix())
        except Exception as error:row.update(status='failed',error_type=type(error).__name__)
        row['elapsed_s']=time.perf_counter()-row_started;save();print(json.dumps(row,ensure_ascii=False),flush=True)
    report['status']='complete' if all(r['status']=='complete' for r in report['recipes']) else 'partial'
    report['elapsed_s']=time.perf_counter()-started;save()
    if report['status']!='complete':raise SystemExit(1)


if __name__=='__main__':main()
