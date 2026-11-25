"""Application admission stays separate from evidence and peer appraisal."""

import hashlib
import json
import os


def save_private(path, record):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(record, stream, indent=2)


def authenticate(app, result, *, attempt=None):
    if result.get("scope") != "evidence_only" or result.get("status") != "verified":
        raise ValueError("Evidence verification did not pass")
    if attempt is None:
        raise ValueError("Live caller context required for admission")
    # Confido serializes a bare HTTPS origin with URL's trailing slash.
    if (
        attempt.result != result
        or attempt.archive["origin"].rstrip("/") != app["origin"].rstrip("/")
    ):
        raise ValueError("Appraisal differs from the selected application endpoint")
    if hashlib.sha256(app["verifier_bytes"]).hexdigest() != result["policy_sha256"]:
        raise ValueError("Verifier policy changed after appraisal")
    return attempt.authenticate_peer()
