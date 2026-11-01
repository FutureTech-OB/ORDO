"""Start only this experiment's native coordinator in a detached session."""
import json
from pathlib import Path
import subprocess
import sys

base=Path(__file__).resolve().parent
out=base/'native-donation-full-grid'
out.mkdir(exist_ok=True)
if (out/'status.json').exists():
    status=json.loads((out/'status.json').read_text())
    if status.get('status')=='running':raise RuntimeError('A coordinator is already marked running; inspect its recorded PID before restarting.')
log=(out/'coordinator.log').open('ab')
cmd=[sys.executable,str(base/'coordinator.py'),'--julia',str(base/'julia-1.10.2/bin/julia'),
     '--output',str(out),'--workers','16','--full-donation-grid']
p=subprocess.Popen(cmd,cwd=base,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(out/'launch.json').write_text(json.dumps(dict(pid=p.pid,command=cmd,output=str(out)),indent=2))
print(json.dumps(dict(pid=p.pid,output=str(out))),flush=True)
