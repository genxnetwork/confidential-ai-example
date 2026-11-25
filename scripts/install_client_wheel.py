"""Explicitly download, validate and install a client wheel; record provenance."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.runtime import INSTALL_RECORD, ROOT
from scripts.download_client_wheel import download_latest


def inspect_wheel(wheel, pin):
    """Reject an unexpected package or unsafe paths before importing candidate code."""
    with zipfile.ZipFile(wheel) as archive:
        entries = archive.namelist()
        metadata = [name for name in entries if name.endswith(".dist-info/METADATA")]
        binaries = [
            name for name in entries
            if name.startswith("confido_client/_native") and name.endswith((".so", ".pyd"))
        ]
        if len(metadata) != 1 or len(binaries) != 1:
            raise ValueError("Confido client wheel needs one metadata and native module")
        required_files = {
            "confido_client/__init__.py",
            "confido_client/httpx_transport.py",
            "confido_client/console.py",
        }
        if not required_files <= set(entries):
            raise ValueError("Confido client wheel needs the Python adapter and console API")
        fields = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
        if fields["Name"].lower().replace("_", "-") != pin["distribution"]:
            raise ValueError("Unexpected wheel distribution")
        if fields["Version"] != pin["version"]:
            raise ValueError("Wheel version differs from pin")
        for name in entries:
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Unsafe wheel path")


def probe(directory):
    """Check the selected import path in a fresh interpreter, avoiding cached modules."""
    code = (
        "import json\n"
        "from demo.runtime import ensure_runtime\n"
        "print(json.dumps(ensure_runtime()))\n"
    )
    return json.loads(subprocess.check_output(
        [sys.executable, "-c", code], cwd=directory, text=True,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join((str(directory), str(ROOT)))),
    ))


def probe_wheel(wheel, directory):
    """Probe the validated candidate without changing the installed distribution."""
    candidate = directory / "candidate"
    candidate.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith("confido_client/"):
                archive.extract(name, candidate)
    return probe(candidate)


def write_install_record(record):
    """Atomically publish provenance after installation and verification succeed."""
    with tempfile.NamedTemporaryFile(
        mode="w", dir=INSTALL_RECORD.parent, delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(record, stream, indent=2)
        stream.write("\n")
    try:
        temporary.replace(INSTALL_RECORD)
    finally:
        temporary.unlink(missing_ok=True)


def install(local_wheel=None):
    """Validate and install one wheel, then compare its installed build and record it.

    A selected local candidate overrides upstream download. Pip checks the wheel
    hash, and a second interpreter must agree with the pre-installation probe.
    """
    pin = json.loads((ROOT / "confido-client-wheel.json").read_text())
    with tempfile.TemporaryDirectory(prefix="confido-install-") as directory:
        stage = Path(directory)
        source = None
        if local_wheel is None:
            wheel, source = download_latest(pin, stage)
        else:
            wheel = Path(local_wheel).resolve()
        inspect_wheel(wheel, pin)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        expected = probe_wheel(wheel, stage)
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--force-reinstall",
            "--no-index", "--no-deps", wheel.as_uri() + "#sha256=" + digest,
        ], check=True)
        # A fresh interpreter must see the newly installed module, not a cached one.
        actual = probe(ROOT)
        if actual != expected:
            raise RuntimeError("Installed client differs from the selected wheel")
        record = {
            "wheel": wheel.name,
            "wheel_sha256": digest,
            "build_info": actual["build_info"],
        }
        if source is not None:
            record["github"] = source
        write_install_record(record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-wheel", type=Path)
    args = parser.parse_args()
    install(args.client_wheel)
