"""Read-only header/population audit of a committed original-scale checkpoint."""
import argparse
from array import array
import json
from pathlib import Path
import struct
import sys


def inspect(path):
    path=Path(path)
    with path.open('rb') as f:
        def read(fmt):
            fmt='<'+fmt;n=struct.calcsize(fmt);raw=f.read(n)
            if len(raw)!=n:raise ValueError('Truncated checkpoint header.')
            return struct.unpack(fmt,raw)[0]
        magic=read('Q')
        if magic not in (0x434d4d46554c4c31,0x434d4d46554c4c32):raise ValueError('Unknown checkpoint format.')
        n=read('i');t=read('i');target=read('i');seed=read('I');rep=read('i');memory=read('i');alpha=read('d');rho=read('d')
        flushed=read('?') if magic==0x434d4d46554c4c32 else False
        arrays=[]
        for _ in range(5):
            raw=f.read(90000*4)
            if len(raw)!=90000*4:raise ValueError('Truncated population arrays.')
            values=array('i');values.frombytes(raw)
            if sys.byteorder!='little':values.byteswap()
            arrays.append(values)
        actual=[p+flow for p,flow in zip(arrays[0],arrays[4])]
        if sum(actual)!=n or sum(arrays[4]) or min(actual)<0:raise ValueError('Population conservation failed.')
        return dict(path=str(path),bytes=path.stat().st_size,format_version=1 if magic==0x434d4d46554c4c31 else 2,
            population=n,committed_period=t,target_periods=target,seed=seed,replicate=rep,memory=bool(memory),
            code_alpha=alpha,rho0=rho,final_flushed=flushed,population_mass=sum(actual),pending_flow_mass=sum(arrays[4]),
            occupied_after_movements=sum(p>0 for p in actual),occupied_frozen_prior=sum(p>0 for p in arrays[0]),
            concentration_after_movements=sum((p/n)**2 for p in actual))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('checkpoint',type=Path)
    print(json.dumps(inspect(p.parse_args().checkpoint),indent=2))
