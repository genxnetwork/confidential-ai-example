"""Show which Confido checkout supplies the development Python environment."""

import importlib.metadata
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


def main() -> None:
    expected = Path(sys.argv[1]).resolve()
    try:
        distribution = importlib.metadata.distribution("confido-atls")
        import confido  # noqa: F401 - also check that the extension can be imported
    except (importlib.metadata.PackageNotFoundError, ImportError) as error:
        raise SystemExit(f"Confido is unavailable in this environment: {error}\nRun make dev-update.")

    try:
        provenance = json.loads(distribution.read_text("direct_url.json") or "{}")
        url = urlsplit(provenance.get("url", ""))
        source = Path(unquote(url.path)).resolve() if url.scheme == "file" else None
    except (ValueError, TypeError):
        source = None

    if source != expected:
        raise SystemExit(
            f"Confido is not installed from {expected}.\n"
            f"Installed source: {source or 'unknown (possibly PyPI)'}\n"
            "Run make dev-update."
        )

    print("Confido development install: OK")
    print(f"  Version: {distribution.version}")
    print(f"  Local source: {source}")
    print(f"  Python environment: {sys.prefix}")


if __name__ == "__main__":
    main()
