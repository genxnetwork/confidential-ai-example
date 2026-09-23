"""Show installed wheel provenance and verify it against the local built artifact."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse
import confido

root=Path(__file__).resolve().parents[1]
dist=importlib.metadata.distribution('confido-atls')
info=json.loads(dist.read_text('direct_url.json') or '{}')
source=Path(unquote(urlparse(info.get('url','')).path))
if getattr(confido,'__version__',None)!='0.3.0':
    raise SystemExit('Stale Confido wheel; run make dev-update')
expected=root/'build/wheels'/source.name
if not expected.is_file():
    raise SystemExit('Local wheel artifact not found; run make dev-update')
digest=hashlib.sha256(expected.read_bytes()).hexdigest()
recorded=info.get('archive_info',{}).get('hashes',{}).get('sha256')
if recorded!=digest:
    raise SystemExit('Installed wheel differs from build/wheels; run make dev-update')
print('Confido:',confido.__version__)
print('Installed from:',source)
print('Wheel SHA-256:',digest)
print('Rust source:',Path(sys.argv[1]).resolve() if len(sys.argv)>1 else 'see build manifest')
