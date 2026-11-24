"""Fingerprint an explicit set of source files, excluding runtime secrets and artifacts."""

import hashlib
import sys
from pathlib import Path


def files(root, scope):
    if scope == "transport":
        base = root / "native_transport"
        paths = list((base / "src").rglob("*.rs"))
        paths += [
            base / name
            for name in ("Cargo.toml", "Cargo.lock", "build.rs", "pyproject.toml")
            if (base / name).is_file()
        ]
        paths += [root / "scripts/source_fingerprint.py"]
        dirs = [base / "src"]
    elif scope == "application":
        paths = [
            root / name
            for name in (
                "confai-promter.py",
                "Makefile",
                "Dockerfile",
                "requirements.lock",
                "confido-source.json",
            )
        ]
        dirs = [root / "demo", root / "scripts"]
        paths += [p for directory in dirs for p in directory.rglob("*.py")]
    else:
        raise ValueError("Unknown source scope")
    return sorted(set(paths)), dirs


def fingerprint(root, scope):
    digest = hashlib.sha256()
    for path in files(root, scope)[0]:
        name, data = path.relative_to(root).as_posix().encode(), path.read_bytes()
        digest.update(
            len(name).to_bytes(8, "big") + name + len(data).to_bytes(8, "big") + data
        )
    return digest.hexdigest()


if __name__ == "__main__":
    root, scope = Path(sys.argv[1]).resolve(), sys.argv[2]
    print(fingerprint(root, scope))
    for path in [*files(root, scope)[0], *files(root, scope)[1]]:
        print(path)
