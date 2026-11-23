"""Install exact local artifacts and retain their digest in pip direct_url metadata."""
import hashlib
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
urls=[]
for line in (root/'build/wheel.sha256').read_text().splitlines():
    digest,name=line.split()
    wheel=(root/'build/wheels'/name).resolve()
    if wheel.parent != (root/'build/wheels').resolve():raise ValueError('Invalid wheel path')
    if hashlib.sha256(wheel.read_bytes()).hexdigest()!=digest:raise ValueError('Wheel hash mismatch')
    urls.append(wheel.as_uri()+'#sha256='+digest)
if len(urls)!=2:raise ValueError('Expected verifier and transport wheel')
subprocess.run([sys.executable,'-m','pip','install','--force-reinstall','--no-index','--no-deps',*urls],check=True)
