"""Rebuild stale development artifacts; subsequent chat starts in a fresh process."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
confido_lib = Path(sys.argv[1]).resolve()
check = subprocess.run(
    [sys.executable, str(root / "scripts/dev_info.py"), str(confido_lib)],
    capture_output=True,
    text=True,
    check=False,
)
if check.returncode:
    print(check.stderr.strip() or check.stdout.strip(), flush=True)
    print("Updating native runtime for this checkout…", flush=True)
    subprocess.run(
        ["make", "dev-update", f"VENV={sys.prefix}", f"CONFIDO_LIB={confido_lib}"],
        cwd=root,
        check=True,
    )
else:
    print(check.stdout.strip())
