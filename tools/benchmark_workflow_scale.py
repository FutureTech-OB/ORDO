"""Free local scale benchmark, including full decision/effect evidence writes.

Each case runs in a fresh process. There is no Jev/mock-HTTP throughput claim.
Run from the repository root after installing its Mesa extra.
"""
import argparse
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time


def peak_memory():
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
                (name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
                    'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize,'Windows PeakWorkingSetSize; includes imported libraries'
    import resource
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value*(1 if sys.platform=='darwin' else 1024),'process ru_maxrss; includes imported libraries'


def worker(agents,rounds,mode,root):
    from examples.large_organization import large_organization_plan
    from orgabm import __version__
    from orgabm.plans import expand_plan
    from orgabm.staged import run_staged_simulation
    from orgabm.workflow_mesa import WorkflowModel,workflow_rule
    import mesa
    start=time.perf_counter()
    plan=large_organization_plan(agents,rounds=rounds,mode=mode)
    expanded=expand_plan(plan)
    config=expanded['configs'][0]
    world=root/f'world-{agents}-{mode}'
    model=WorkflowModel(config)
    init_s=time.perf_counter()-start
    result=run_staged_simulation(model,workflow_rule(),rounds=rounds,seed=config['seed'],output=world)
    snapshot=model.snapshot()
    (world/'workflow-state.json').write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
    (world/'plan.json').write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
    total_s=time.perf_counter()-start
    final=result['metrics'][-1]
    assert result['status']=='complete' and result['completed_rounds']==rounds
    assert math.isclose(sum(snapshot['earnings']),final['net_value'],abs_tol=1e-6,rel_tol=1e-9)
    if mode=='delegated':
        assert result['decisions']==len(config['tasks'])*rounds
        assert final['completed_tasks']==len(config['tasks'])
    memory,definition=peak_memory()
    summary=dict(version=__version__,python=platform.python_version(),mesa=mesa.__version__,platform=platform.platform(),
        agents=agents,departments=config['departments'],tasks=len(config['tasks']),rounds=rounds,mode=mode,
        decisions=result['decisions'],initialization_s=init_s,runner_s=result['elapsed_s'],
        total_s=total_s,decisions_per_total_second=result['decisions']/total_s,
        peak_memory_mib=memory/1024**2,memory_definition=definition,
        event_log_mib=(world/'events.jsonl').stat().st_size/1024**2,
        evidence_mib=sum(p.stat().st_size for p in world.iterdir() if p.is_file())/1024**2,
        completed_tasks=final['completed_tasks'],queue_wait_ticks=final['cumulative']['queue_wait_ticks'],
        net_value=final['net_value'],provider_requests=0,
        scope='Single fresh process; rule decisions; full traces and snapshots; synthetic Personas/tasks. No HTTP inference, MCP service, browser or market simulation.')
    (root/f'summary-{agents}-{mode}.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes',type=int,nargs='+',default=[1000,10000])
    parser.add_argument('--rounds',type=int,default=6)
    parser.add_argument('--modes',nargs='+',choices=['delegated','reviewed'],default=['delegated','reviewed'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:
        worker(args.sizes[0],args.rounds,args.modes[0],args.output)
        return
    # Validate before creating a result directory or starting a subprocess.
    from examples.large_organization import large_organization_plan
    for size in args.sizes:
        large_organization_plan(size,rounds=args.rounds)
    if len(set(args.sizes))!=len(args.sizes) or len(set(args.modes))!=len(args.modes):
        parser.error('Sizes and modes must be distinct.')
    args.output.mkdir(parents=True,exist_ok=False)
    results=[]
    for size in args.sizes:
        for mode in args.modes:
            subprocess.run([sys.executable,__file__,'--worker','--sizes',str(size),'--rounds',str(args.rounds),
                '--modes',mode,'--output',str(args.output)],check=True,timeout=300)
            results.append(json.loads((args.output/f'summary-{size}-{mode}.json').read_text(encoding='utf-8')))
            (args.output/'benchmark.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__':main()
