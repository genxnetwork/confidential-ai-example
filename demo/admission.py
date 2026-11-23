"""Application decisions are separate from evidence verification results."""

import base64
import json
import os

from _confai_transport import Session


def save_private(path, record):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(record, stream, indent=2)


def authenticate(app, result, *, run=None):
    if result.get("scope") != "evidence_only" or result.get("status") != "verified":
        raise ValueError("Evidence verification did not pass")
    if run is None:
        raise ValueError("Live caller context required for admission")
    run.ensure_current(app, result)
    certificate = base64.b64decode(
        result["verified_artifacts"]["certificate_der_base64"], validate=True
    )
    session = Session(app["origin"], certificate)
    status, _, _ = session.request(
        "HEAD", app["origin"].rstrip("/") + "/tee-report", [], b""
    )
    if status != 204:
        raise ValueError("Attestation endpoint unavailable on the appraised HTTPS peer")
    run.ensure_current(app, result)
    return session
