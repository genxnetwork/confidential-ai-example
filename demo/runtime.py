"""Verify the installed Confido client against the local runtime manifest."""

import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_REVISION = 2


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_digest(root, scope):
    output = subprocess.check_output(
        [sys.executable, str(root / "scripts/source_fingerprint.py"), str(root), scope],
        text=True,
    )
    return output.splitlines()[0]


def ensure_runtime():
    try:
        manifest = json.loads((ROOT / "build/runtime.json").read_bytes())
        if (
            manifest["schema_version"] != 2
            or manifest["pipeline_revision"] != PIPELINE_REVISION
        ):
            raise ValueError("Unsupported runtime manifest/pipeline")
        pin = json.loads((ROOT / "confido-client-wheel.json").read_text())
        if manifest["client_distribution"] != f"confido-client=={pin['version']}":
            raise ValueError("Client distribution differs from pin")
        module = importlib.import_module("confido_client._native")
        artifact = manifest["artifact"]
        if file_digest(module.__file__) != artifact["binary_sha256"]:
            raise ValueError("Loaded Confido client binary differs from manifest")
        package_dir = Path(module.__file__).parent
        for name, expected in artifact["python_files"].items():
            relative = Path(name)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or file_digest(package_dir / relative) != expected
            ):
                raise ValueError("Loaded Confido client Python adapter differs from manifest")
        info = module.build_info()
        if info != artifact["build_info"]:
            raise ValueError("Loaded Confido client build metadata differs from manifest")
        if info["client"]["core"]["pipeline_revision"] != PIPELINE_REVISION:
            raise ValueError("Verifier pipeline is incompatible with this caller")
        for part in (info["client"]["core"], info["client"]["wrapper"], info["wrapper"]):
            if part["version"] != pin["version"]:
                raise ValueError("Loaded Confido client version differs from pin")
        for actual, expected in (
            (info["client"]["core"]["source_sha256"], pin["core_source_sha256"]),
            (info["client"]["wrapper"]["source_sha256"], pin["client_source_sha256"]),
            (info["wrapper"]["source_sha256"], pin["wrapper_source_sha256"]),
        ):
            if actual != expected:
                raise ValueError("Loaded Confido client sources differ from pin")
        if source_digest(ROOT, "application") != manifest["sources"]["application"]:
            raise ValueError("Caller sources differ from runtime manifest")
        if os.environ.get("CONFIDO_RUNTIME_MODE") != "packaged":
            wheel = ROOT / "build/wheels" / artifact["wheel"]
            if (
                not wheel.is_file()
                or file_digest(wheel) != artifact["wheel_sha256"]
            ):
                raise ValueError("Local wheel differs from runtime manifest or is missing")
        return {
            "pipeline_revision": PIPELINE_REVISION,
            "artifacts": {"confido-client": artifact},
            "caller_source_sha256": manifest["sources"]["application"],
        }
    except (
        OSError,
        ValueError,
        KeyError,
        AttributeError,
        ImportError,
        subprocess.CalledProcessError,
    ) as error:
        raise RuntimeError(
            f"Runtime is stale or incompatible: {error}. Run make dev-update."
        ) from error
