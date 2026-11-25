"""Download the released verifier wheel and build the application transport wheel."""

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


def verifier_version():
    config = json.loads((ROOT / "confido-wheel.json").read_text())
    if config["distribution"] != "confido-verifier":
        raise ValueError("Unexpected verifier distribution")
    return config["version"]


def check_verifier_wheel(wheel, version):
    with zipfile.ZipFile(wheel) as archive:
        records = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(records) != 1:
            raise ValueError("Verifier wheel needs exactly one metadata file")
        metadata = Parser().parsestr(archive.read(records[0]).decode("utf-8"))
        if metadata["Name"].lower().replace("_", "-") != "confido-verifier":
            raise ValueError("Downloaded wheel is not confido-verifier")
        if metadata["Version"] != version:
            raise ValueError("Downloaded verifier version differs from pin")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--maturin", required=True)
    parser.add_argument("--verifier-wheel", type=Path, help="Existing released wheel for offline builds")
    args = parser.parse_args()
    version = verifier_version()

    def snapshot():
        return {
            "transport": source_digest(ROOT, "transport"),
            "application": source_digest(ROOT, "application"),
        }

    before = snapshot()
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wheel-build-", dir=ROOT / "build") as directory:
        stage = Path(directory)
        if args.verifier_wheel:
            shutil.copy2(args.verifier_wheel, stage / args.verifier_wheel.name)
        else:
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "download", "--no-deps",
                    "--only-binary=:all:", "--index-url", "https://pypi.org/simple",
                    "--dest", str(stage),
                    f"confido-verifier=={version}",
                ],
                check=True,
            )
        verifier_wheels = list(stage.glob("confido_verifier-*.whl"))
        if len(verifier_wheels) != 1:
            raise RuntimeError("Expected one compatible released verifier wheel")
        check_verifier_wheel(verifier_wheels[0], version)

        manifest = ROOT / "native_transport/Cargo.toml"
        subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/prepare_attribution.py"),
                str(manifest), str(manifest.parent / "licenses"),
                "--project-root", str(ROOT),
            ],
            check=True,
        )
        subprocess.run(
            [
                args.maturin, "build", "--locked", "--release",
                "--manifest-path", str(manifest),
                "--interpreter", sys.executable, "--out", str(stage),
            ],
            check=True,
        )
        if before != snapshot():
            raise RuntimeError("Sources changed during build; repeat make dev-update")

        artifacts = {}
        unpacked = stage / "probe"
        unpacked.mkdir()
        for wheel in sorted(stage.glob("*.whl")):
            name = (
                "confido-verifier" if wheel.name.startswith("confido_verifier-")
                else "confai-transport" if wheel.name.startswith("confai_transport-")
                else None
            )
            if name is None or name in artifacts:
                raise RuntimeError("Unexpected or ambiguous wheel output")
            with zipfile.ZipFile(wheel) as archive:
                binaries = [p for p in archive.namelist() if p.endswith((".so", ".pyd"))]
                if len(binaries) != 1:
                    raise RuntimeError("Expected exactly one native artifact")
                artifacts[name] = {
                    "wheel": wheel.name,
                    "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                    "binary": binaries[0],
                    "binary_sha256": hashlib.sha256(archive.read(binaries[0])).hexdigest(),
                }
                archive.extractall(unpacked)
        if set(artifacts) != {"confido-verifier", "confai-transport"}:
            raise RuntimeError("Expected verifier and transport wheels")
        probe = """\
import json
import confido_verifier
import _confai_transport
print(json.dumps({
    "confido-verifier": confido_verifier.build_info(),
    "confai-transport": _confai_transport.build_info(),
}))
"""
        infos = json.loads(
            subprocess.check_output(
                [sys.executable, "-c", probe], cwd=stage,
                env=dict(os.environ, PYTHONPATH=str(unpacked)), text=True,
            )
        )
        verifier = infos["confido-verifier"]
        if verifier["core"]["pipeline_revision"] != PIPELINE_REVISION:
            raise RuntimeError("Unexpected verifier pipeline")
        if any(verifier[part]["version"] != version for part in ("core", "wrapper")):
            raise RuntimeError("Verifier embedded version differs from pin")
        if (
            infos["confai-transport"]["source_sha256"] != before["transport"]
            or before != snapshot()
        ):
            raise RuntimeError("Built artifact does not match the captured sources")

        destination = ROOT / "build/wheels"
        destination.mkdir(exist_ok=True)
        for wheel in destination.glob("*.whl"):
            wheel.unlink()
        for name, item in artifacts.items():
            item["build_info"] = infos[name]
            shutil.copy2(stage / item["wheel"], destination / item["wheel"])
        runtime = {
            "schema_version": 2,
            "pipeline_revision": PIPELINE_REVISION,
            "verifier_distribution": f"confido-verifier=={version}",
            "sources": before,
            "artifacts": artifacts,
        }
        (ROOT / "build/wheel.sha256").write_text(
            "".join(f"{v['wheel_sha256']}  {v['wheel']}\n" for v in artifacts.values())
        )
        temporary = ROOT / "build/runtime.json.tmp"
        temporary.write_text(json.dumps(runtime, indent=2) + "\n")
        temporary.replace(ROOT / "build/runtime.json")
        print("Prepared runtime manifest for pipeline", PIPELINE_REVISION)


if __name__ == "__main__":
    main()
