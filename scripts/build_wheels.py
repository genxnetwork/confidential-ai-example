"""Build, fingerprint and probe both wheels before publishing a local runtime manifest."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.runtime import PIPELINE_REVISION, ROOT, source_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confido-lib", type=Path, required=True)
    parser.add_argument("--maturin", required=True)
    args = parser.parse_args()
    core = args.confido_lib.resolve().parent

    def snapshot():
        return {
            "core": source_digest(core, "core"),
            "python": source_digest(core, "python"),
            "transport": source_digest(ROOT, "transport"),
            "application": source_digest(ROOT, "application"),
        }

    before = snapshot()
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="wheel-build-", dir=ROOT / "build"
    ) as directory:
        stage = Path(directory)
        for manifest in (
            core / "bindings/python/Cargo.toml",
            ROOT / "native_transport/Cargo.toml",
        ):
            subprocess.run(
                [
                    args.maturin,
                    "build",
                    "--locked",
                    "--release",
                    "--manifest-path",
                    str(manifest),
                    "--interpreter",
                    sys.executable,
                    "--out",
                    str(stage),
                ],
                check=True,
            )
        after = snapshot()
        if before != after:
            raise RuntimeError("Sources changed during build; repeat make dev-update")
        artifacts = {}
        unpacked = stage / "probe"
        unpacked.mkdir()
        for wheel in sorted(stage.glob("*.whl")):
            name = (
                "confido-verifier"
                if wheel.name.startswith("confido_verifier-")
                else "confai-transport"
            )
            if name in artifacts:
                raise RuntimeError("Ambiguous wheel outputs")
            with zipfile.ZipFile(wheel) as archive:
                binaries = [p for p in archive.namelist() if p.endswith(".so")]
                if len(binaries) != 1:
                    raise RuntimeError("Expected exactly one native artifact")
                artifacts[name] = {
                    "wheel": wheel.name,
                    "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                    "binary": binaries[0],
                    "binary_sha256": hashlib.sha256(
                        archive.read(binaries[0])
                    ).hexdigest(),
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
                [sys.executable, "-c", probe],
                cwd=stage,
                env=dict(os.environ, PYTHONPATH=str(unpacked)),
                text=True,
            )
        )
        if infos["confido-verifier"]["core"]["pipeline_revision"] != PIPELINE_REVISION:
            raise RuntimeError("Unexpected verifier pipeline")
        embedded = {
            "core": infos["confido-verifier"]["core"]["source_sha256"],
            "python": infos["confido-verifier"]["wrapper"]["source_sha256"],
            "transport": infos["confai-transport"]["source_sha256"],
        }
        if (
            any(before[key] != value for key, value in embedded.items())
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
        manifest = {
            "schema_version": 1,
            "pipeline_revision": PIPELINE_REVISION,
            "confido_root": str(core),
            "sources": before,
            "artifacts": artifacts,
        }
        (ROOT / "build/wheel.sha256").write_text(
            "".join(f"{v['wheel_sha256']}  {v['wheel']}\n" for v in artifacts.values())
        )
        temporary = ROOT / "build/runtime.json.tmp"
        temporary.write_text(json.dumps(manifest, indent=2) + "\n")
        temporary.replace(ROOT / "build/runtime.json")
        print("Built runtime manifest for pipeline", PIPELINE_REVISION)


if __name__ == "__main__":
    main()
