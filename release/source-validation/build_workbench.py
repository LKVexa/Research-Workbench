"""Build a new separately versioned local workbench candidate."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FOUNDATION=Path('C:/Users/russe/Documents/Codex/2026-10-30/ple/outputs/Shared_Foundation_v0.1.0-rc.1/foundation')
PIN='e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build(dest):
    allowed=ROOT.parents[1]/'validation'
    dest=dest.resolve()
    dest.relative_to(allowed.resolve())
    assert sha(FOUNDATION/'MANIFEST.json')==PIN
    q6=json.loads((FOUNDATION.parent/'gates/Q6.json').read_text(encoding='utf-8'))
    assert q6['result']=='pass' and q6['foundation_manifest_sha256']==PIN
    dest.mkdir(parents=True,exist_ok=False)
    shutil.copytree(FOUNDATION,dest/'foundation')
    for name in ('workbench.py','Start-Workbench.ps1','Workbench.cmd'):
        shutil.copy2(ROOT/name,dest/name)
    expected=['START_HERE.md','ARCHITECTURE.md','WORKBENCH-CONTRACTS.md','CHANGELOG.md','ROLLBACK.md','KNOWN-LIMITATIONS.md']
    for name in expected:
        shutil.copy2(ROOT/'docs'/name,dest/name)
    files={p.relative_to(dest).as_posix():sha(p) for p in sorted(dest.iterdir()) if p.is_file()}
    manifest={'schema_version':'1.0.0','product':'local-component-workbench','version':'0.1.0-rc.1',
              'foundation_version':'0.1.0-rc.1','foundation_manifest_sha256':PIN,'files':files,
              'supported_platform':'Windows','scope':'Three bounded fixture capabilities plus full393-entry catalog',
              'other_products':{'coding-agent':'deferred','research-toolkit':'deferred'}}
    (dest/'PRODUCT-MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({'candidate':str(dest),'product_manifest_sha256':sha(dest/'PRODUCT-MANIFEST.json'),'foundation_manifest_sha256':PIN}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True)
    build(p.parse_args().destination)
