"""Check current sources, wheel provenance and the actual loaded native modules."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.runtime import ensure_runtime

if __name__ == '__main__':
    try:
        info = ensure_runtime(sys.argv[1] if len(sys.argv) > 1 else None)
    except RuntimeError as error:
        raise SystemExit(str(error))
    print('Runtime verified; pipeline', info['pipeline_revision'])
    for name, artifact in info['artifacts'].items():
        print(name, artifact['binary_sha256'])
