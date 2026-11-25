"""Install the exact staged client wheel recorded in the local runtime manifest."""

import hashlib
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
lines = (root / "build/wheel.sha256").read_text().splitlines()
if len(lines) != 1:
    raise ValueError("Expected one Confido client wheel")
digest, name = lines[0].split()
wheel = (root / "build/wheels" / name).resolve()
if wheel.parent != (root / "build/wheels").resolve():
    raise ValueError("Invalid wheel path")
if hashlib.sha256(wheel.read_bytes()).hexdigest() != digest:
    raise ValueError("Wheel hash mismatch")
subprocess.run(
    [
        sys.executable, "-m", "pip", "install", "--force-reinstall",
        "--no-index", "--no-deps", wheel.as_uri() + "#sha256=" + digest,
    ],
    check=True,
)
