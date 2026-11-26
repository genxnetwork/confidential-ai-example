"""Check the public client API used by the example; never install dependencies."""

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_REVISION = 2
INSTALL_RECORD = Path(sys.prefix) / "confido-client-install.json"


def validate_build_info(info, version):
    """Require the supported pipeline and pinned SDK; native versions are diagnostic."""
    if info["client"]["core"]["pipeline_revision"] != PIPELINE_REVISION:
        raise ValueError("Unsupported verifier pipeline")
    if info["wrapper"]["version"] != version:
        raise ValueError("Confido client version is incompatible")


def ensure_runtime():
    """Return installed client metadata, or fail before any login or collection."""
    try:
        if sys.version_info[:2] != (3, 15):
            raise ValueError("Python 3.15 is required")
        pin = json.loads((ROOT / "confido-client-wheel.json").read_text())
        client = importlib.import_module("confido_client")
        console = importlib.import_module("confido_client.console")
        transport = importlib.import_module("confido_client.httpx_transport")
        required_apis = (
            (client, "appraise"),
            (console, "print_verification"),
            (transport, "ScopedTransport"),
        )
        for module, name in required_apis:
            if not callable(getattr(module, name, None)):
                raise ValueError(f"Confido client is missing {name}")
        info = client.build_info()
        validate_build_info(info, pin["version"])
        return {
            "pipeline_revision": PIPELINE_REVISION,
            "client_distribution": f"confido-client=={pin['version']}",
            "build_info": info,
        }
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, OSError) as error:
        raise RuntimeError(f"Client is incompatible: {error}. Run ./run --update.") from error


def main():
    """Show installed compatibility and optional build provenance without network I/O."""
    try:
        snapshot = ensure_runtime()
    except RuntimeError as error:
        raise SystemExit(str(error))
    print(snapshot["client_distribution"], "pipeline", snapshot["pipeline_revision"])
    print("Client source:", snapshot["build_info"]["client"]["wrapper"]["source_sha256"])
    try:
        record = json.loads(INSTALL_RECORD.read_text())
        if record["build_info"] == snapshot["build_info"]:
            print("Installed wheel:", record["wheel"], "SHA-256", record["wheel_sha256"])
            if "github" in record:
                source = record["github"]
                print("GitHub:", source["repository"], "run", source["run_id"],
                      "commit", source["source_commit"])
        else:
            print("Installation record describes a different client build.")
    except (OSError, ValueError, KeyError, TypeError):
        print("No installation provenance recorded; client API is compatible.")


if __name__ == "__main__":
    main()
