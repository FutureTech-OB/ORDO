"""Retrieve and verify the declared small subset of public upstream files."""
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.parse


def load_sources(root,download=False):
    manifest=json.loads(Path(__file__).with_name('source_manifest.json').read_text(encoding='utf-8'))
    root=Path(root)
    for row in manifest['files']:
        path=root/row['path']
        if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Invalid upstream path.')
        if not path.exists() and download:
            url=f"https://raw.githubusercontent.com/{manifest['repo']}/{manifest['commit']}/"+urllib.parse.quote(row['path'],safe='/')
            with urllib.request.urlopen(url,timeout=45) as response:data=response.read(row['bytes']+1)
            if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Upstream bytes mismatch.')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Cached upstream hash mismatch: '+row['path'])
    return manifest
