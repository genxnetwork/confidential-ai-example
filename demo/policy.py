"""Load caller-owned application and verifier policies from local files."""

import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

MAX_POLICY_BYTES = 64 * 1024


def prepare_genoa_profiles(destination=None):
    """Prepare private application policies that select the enrolled Genoa pair."""
    root = Path(__file__).resolve().parents[1]
    destination = Path(destination or root / ".artifacts/genoa-console-profiles").resolve()
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    for source, name in (
        ("match.json", "match.json"), ("mismatch.json", "mismatch.json"),
        ("verifier-genoa-stage-registry.json", "verifier-match.json"),
        ("verifier-genoa-stage-mismatch.json", "verifier-mismatch.json"),
    ):
        target = destination / name
        shutil.copyfile(root / "profiles" / source, target)
        target.chmod(0o600)
    return destination


def load_policy(path):
    """Read bounded local policies and reject origins or paths outside their scope."""
    path = Path(path)
    with path.open("rb") as source:
        raw = source.read(MAX_POLICY_BYTES + 1)
    if len(raw) > MAX_POLICY_BYTES:
        raise ValueError("Application policy exceeds limit")
    app = json.loads(raw)
    if app.get("schema_version") != 2:
        raise ValueError("Application policy version 2 required")

    origin = urlsplit(app["origin"])
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path not in ("", "/")
        or origin.query
        or origin.fragment
    ):
        raise ValueError("Expected bare HTTPS origin")

    parent = path.parent.resolve()
    verifier_path = (parent / app["verifier_policy"]).resolve()
    if not verifier_path.is_relative_to(parent):
        raise ValueError("Verifier policy must be local to the policy directory")
    with verifier_path.open("rb") as source:
        verifier_bytes = source.read(MAX_POLICY_BYTES + 1)
    if len(verifier_bytes) > MAX_POLICY_BYTES:
        raise ValueError("Verifier policy exceeds limit")
    return dict(app, verifier_bytes=verifier_bytes, verifier=json.loads(verifier_bytes))
