"""Verify the identities of loaded native artifacts before contacting a service."""

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


def ensure_runtime(confido_lib=None):
    try:
        manifest = json.loads((ROOT / "build/runtime.json").read_bytes())
        if (
            manifest["schema_version"] != 1
            or manifest["pipeline_revision"] != PIPELINE_REVISION
        ):
            raise ValueError("Unsupported runtime manifest/pipeline")
        infos = {}
        for name, module_name in [
            ("confido-verifier", "confido_verifier.confido_verifier"),
            ("confai-transport", "_confai_transport._confai_transport"),
        ]:
            module = importlib.import_module(module_name)
            item = manifest["artifacts"][name]
            if file_digest(module.__file__) != item["binary_sha256"]:
                raise ValueError(
                    f"Loaded {name} binary differs from manifest: {module.__file__}"
                )
            info = module.build_info()
            if info != item["build_info"]:
                raise ValueError(f"Loaded {name} build metadata differs from manifest")
            infos[name] = info
        if infos["confido-verifier"]["core"]["pipeline_revision"] != PIPELINE_REVISION:
            raise ValueError("Verifier pipeline is incompatible with this caller")
        if source_digest(ROOT, "application") != manifest["sources"]["application"]:
            raise ValueError("Caller sources differ from runtime manifest")
        if os.environ.get("CONFIDO_RUNTIME_MODE") != "packaged":
            core_root = (
                Path(confido_lib).resolve().parent
                if confido_lib
                else Path(manifest["confido_root"])
            )
            actual = {
                "core": source_digest(core_root, "core"),
                "python": source_digest(core_root, "python"),
                "transport": source_digest(ROOT, "transport"),
            }
            for scope, digest in actual.items():
                if digest != manifest["sources"][scope]:
                    raise ValueError(f"{scope} sources changed since wheel build")
            if (
                infos["confido-verifier"]["core"]["source_sha256"] != actual["core"]
                or infos["confido-verifier"]["wrapper"]["source_sha256"]
                != actual["python"]
            ):
                raise ValueError("Verifier embedded sources differ from checkout")
            if infos["confai-transport"]["source_sha256"] != actual["transport"]:
                raise ValueError("Transport embedded sources differ from checkout")
            for item in manifest["artifacts"].values():
                if (
                    file_digest(ROOT / "build/wheels" / item["wheel"])
                    != item["wheel_sha256"]
                ):
                    raise ValueError("Local wheel differs from runtime manifest")
        return {
            "pipeline_revision": PIPELINE_REVISION,
            "artifacts": manifest["artifacts"],
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
