"""Record exactly which local wheel and container were built; never read secrets."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
wheel = next((root / "build/wheels").glob("confido_atls-0.3.0-*.whl"))
image = subprocess.check_output(sys.argv[1:] + ["image", "inspect", "confidential-ai-example:0.3.0", "--format", "{{.Id}}"], text=True).strip()
manifest = {"captured_at": datetime.now(timezone.utc).isoformat(), "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "image": image,
            "base_image": "ubuntu:22.04@sha256:2edbbc5dc405e9612ba3584ce95480277e3eb374407b5505fe26f17df77c7dbc",
            "python_lock_sha256": hashlib.sha256((root / "requirements.lock").read_bytes()).hexdigest(),
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root))}
(root / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
