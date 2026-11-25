"""Prepare project and resolved dependency attribution for a binary package."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from collect_licenses import collect

ROOT = Path(__file__).resolve().parents[1]


def prepare(manifest, destination, project_root=ROOT, *, target=None):
    target = target or os.environ.get("CARGO_BUILD_TARGET")
    if target is None:
        toolchain = subprocess.check_output(["rustc", "-vV"], text=True)
        target = next(
            line.removeprefix("host: ")
            for line in toolchain.splitlines()
            if line.startswith("host: ")
        )
    metadata = json.loads(
        subprocess.check_output(
            [
                "cargo",
                "metadata",
                "--locked",
                "--format-version",
                "1",
                "--filter-platform",
                target,
                "--manifest-path",
                str(manifest),
            ],
            text=True,
        )
    )
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project_root / "LICENSE", destination / "LICENSE")
    notices = project_root / "THIRD_PARTY_NOTICES.md"
    if notices.is_file():
        shutil.copyfile(notices, destination / notices.name)
    collect(metadata, destination / "third-party-licenses.tar.gz")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument(
        "--target", help="Rust target; defaults to CARGO_BUILD_TARGET or the host"
    )
    args = parser.parse_args()
    prepare(
        args.manifest.resolve(),
        args.destination.resolve(),
        args.project_root.resolve(),
        target=args.target,
    )
