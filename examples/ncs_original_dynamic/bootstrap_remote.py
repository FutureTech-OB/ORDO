"""Install official Julia into this isolated task folder; no system changes."""
import hashlib
import json
from pathlib import Path
import platform
import os
import tarfile
import urllib.request


def main():
    base=Path(__file__).resolve().parent
    if platform.machine() not in ('x86_64','AMD64'):raise RuntimeError('Expected official x86_64 Julia binary.')
    name='julia-1.10.2-linux-x86_64.tar.gz'
    checkfile=base/'julia-1.10.2.sha256'
    checks=checkfile.read_text() if checkfile.exists() else urllib.request.urlopen('https://julialang-s3.julialang.org/bin/checksums/julia-1.10.2.sha256',timeout=60).read().decode()
    expected=next(line.split()[0] for line in checks.splitlines() if line.endswith(name))
    archive=base/name
    if not archive.exists():
        with urllib.request.urlopen('https://julialang-s3.julialang.org/bin/linux/x64/1.10/'+name,timeout=90) as r:
            raw=r.read(230_000_001)
        if len(raw)>230_000_000:raise ValueError('Download size exceeded bound.')
        archive.write_bytes(raw)
    actual=hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual!=expected:raise ValueError('Official Julia checksum mismatch.')
    if not (base/'julia-1.10.2/bin/julia').exists():
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if os.path.commonpath([str((base/member.name).resolve()),str(base)])!=str(base):raise ValueError('Unsafe extraction target.')
            tar.extractall(base)
    (base/'runtime.json').write_text(json.dumps(dict(version='1.10.2',archive=name,sha256=actual,
        official_checksum_verified=True,binary=str(base/'julia-1.10.2/bin/julia')),indent=2))
    print((base/'julia-1.10.2/bin/julia').as_posix(),flush=True)


if __name__=='__main__':main()
