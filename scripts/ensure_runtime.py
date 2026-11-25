"""Rebuild stale development artifacts; subsequent chat starts in a fresh process."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
check = subprocess.run(
    [sys.executable, str(root / "scripts/dev_info.py")],
    capture_output=True,
    text=True,
    check=False,
)
if check.returncode:
    print(check.stderr.strip() or check.stdout.strip(), flush=True)
    print("Updating native runtime for this checkout…", flush=True)
    subprocess.run(
        ["make", "dev-update", f"VENV={sys.prefix}"],
        cwd=root,
        check=True,
    )
else:
    print(check.stdout.strip())
