"""Record exactly which local wheel and container were built; never read secrets."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
wheels = sorted((root / "build/wheels").glob("*.whl"))
assert len(wheels) == 1, "Expected one Confido client wheel"
if len(sys.argv) < 3:
    raise SystemExit("Usage: build_manifest.py DOCKER_COMMAND IMAGE_TAG")
image = subprocess.check_output(
    sys.argv[1:-1] + ["image", "inspect", sys.argv[-1], "--format", "{{.Id}}"],
    text=True,
).strip()
manifest = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "wheels": {w.name: hashlib.sha256(w.read_bytes()).hexdigest() for w in wheels},
    "image": image,
    "base_image": "ubuntu:22.04@sha256:2edbbc5dc405e9612ba3584ce95480277e3eb374407b5505fe26f17df77c7dbc",
    "python_lock_sha256": hashlib.sha256(
        (root / "requirements.lock").read_bytes()
    ).hexdigest(),
    "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip(),
    "runtime": json.loads((root / "build/runtime.json").read_bytes()),
    "source_dirty": bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=root)
    ),
}
(root / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
