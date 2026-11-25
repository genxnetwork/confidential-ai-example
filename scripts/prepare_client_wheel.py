"""Stage one pinned Confido client wheel and record its loaded build identity."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.runtime import PIPELINE_REVISION, ROOT, source_digest


def load_pin():
    pin = json.loads((ROOT / "confido-client-wheel.json").read_text())
    if pin["distribution"] != "confido-client" or pin["version"] != "0.2.0":
        raise ValueError("Unexpected Confido client pin")
    return pin


def inspect_wheel(wheel, pin):
    with zipfile.ZipFile(wheel) as archive:
        entries = archive.namelist()
        metadata = [name for name in entries if name.endswith(".dist-info/METADATA")]
        binaries = [
            name for name in entries
            if name.startswith("confido_client/_native") and name.endswith((".so", ".pyd"))
        ]
        if len(metadata) != 1 or len(binaries) != 1:
            raise ValueError("Confido client wheel needs one metadata and native module")
        python_files = {
            name.removeprefix("confido_client/"): hashlib.sha256(archive.read(name)).hexdigest()
            for name in entries
            if name.startswith("confido_client/") and name.endswith(".py")
        }
        if not {"__init__.py", "httpx_transport.py"} <= python_files.keys():
            raise ValueError("Confido client wheel is missing its Python adapter")
        fields = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
        if fields["Name"].lower().replace("_", "-") != pin["distribution"]:
            raise ValueError("Unexpected wheel distribution")
        if fields["Version"] != pin["version"]:
            raise ValueError("Wheel version differs from pin")
        return (
            binaries[0],
            hashlib.sha256(archive.read(binaries[0])).hexdigest(),
            python_files,
        )


def probe_build_info(wheel, destination):
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe wheel path")
            if name.startswith("confido_client/"):
                archive.extract(name, destination)
    probe = "import json, confido_client; print(json.dumps(confido_client.build_info()))"
    return json.loads(
        subprocess.check_output(
            [sys.executable, "-c", probe],
            cwd=destination,
            env=dict(os.environ, PYTHONPATH=str(destination)),
            text=True,
        )
    )


def validate_build_info(info, pin):
    if info["client"]["core"]["pipeline_revision"] != PIPELINE_REVISION:
        raise ValueError("Unexpected verifier pipeline")
    for part in (info["client"]["core"], info["client"]["wrapper"], info["wrapper"]):
        if part["version"] != pin["version"]:
            raise ValueError("Embedded Confido version differs from pin")
    for actual, expected in (
        (info["client"]["core"]["source_sha256"], pin["core_source_sha256"]),
        (info["client"]["wrapper"]["source_sha256"], pin["client_source_sha256"]),
        (info["wrapper"]["source_sha256"], pin["wrapper_source_sha256"]),
    ):
        if actual != expected:
            raise ValueError("Confido client source identity differs from pin")


def prepare(local_wheel=None):
    pin = load_pin()
    before = source_digest(ROOT, "application")
    if local_wheel is None:
        staged = list((ROOT / "build/wheels").glob("*.whl"))
        if len(staged) != 1:
            raise ValueError(
                "Supply CONFIDO_CLIENT_WHEEL=/path/to/confido_client-0.2.0.whl "
                "for the first build"
            )
        local_wheel = staged[0]
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="client-wheel-", dir=ROOT / "build") as directory:
        stage = Path(directory)
        local_wheel = Path(local_wheel).resolve()
        shutil.copy2(local_wheel, stage / local_wheel.name)
        wheels = list(stage.glob("*.whl"))
        if len(wheels) != 1:
            raise ValueError("Expected exactly one Confido client wheel")
        wheel = wheels[0]
        binary, binary_sha256, python_files = inspect_wheel(wheel, pin)
        info = probe_build_info(wheel, stage / "probe")
        validate_build_info(info, pin)
        if source_digest(ROOT, "application") != before:
            raise RuntimeError("Application sources changed during wheel preparation")

        destination = ROOT / "build/wheels"
        destination.mkdir(exist_ok=True)
        for previous in destination.glob("*.whl"):
            previous.unlink()
        shutil.copy2(wheel, destination / wheel.name)
        artifact = {
            "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "binary": binary,
            "binary_sha256": binary_sha256,
            "python_files": python_files,
            "build_info": info,
        }
        runtime = {
            "schema_version": 2,
            "pipeline_revision": PIPELINE_REVISION,
            "client_distribution": f"confido-client=={pin['version']}",
            "sources": {"application": before},
            "artifact": artifact,
        }
        (ROOT / "build/wheel.sha256").write_text(
            f"{artifact['wheel_sha256']}  {wheel.name}\n"
        )
        temporary = ROOT / "build/runtime.json.tmp"
        temporary.write_text(json.dumps(runtime, indent=2) + "\n")
        temporary.replace(ROOT / "build/runtime.json")
    return runtime


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-wheel", type=Path)
    args = parser.parse_args()
    prepare(args.client_wheel)
