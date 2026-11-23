"""Caller-owned, one-use admission context; archives cannot restore a live run."""

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class LiveRun:
    result: dict
    archive: dict
    deadline: float
    policy_sha256: str
    timings: dict
    used: bool = field(default=False, init=False)
    _result_digest: str = field(init=False)
    _archive_digest: str = field(init=False)

    def __post_init__(self):
        self._result_digest = _digest(self.result)
        self._archive_digest = _digest(self.archive)

    def ensure_current(self, app, result):
        if self.used:
            raise ValueError("Challenge has already been used for admission")
        if time.monotonic() >= self.deadline:
            raise ValueError("Challenge deadline expired")
        if (
            self.archive.get("mode") != "live_collection"
            or self.archive.get("origin") != app["origin"]
        ):
            raise ValueError("Admission requires a live run for this origin")
        if hashlib.sha256(app["verifier_bytes"]).hexdigest() != self.policy_sha256:
            raise ValueError("Application policy changed after verification")
        if (
            _digest(result) != self._result_digest
            or _digest(self.archive) != self._archive_digest
        ):
            raise ValueError("Verification result or inputs changed after collection")
        context, inputs = self.archive["context"], self.archive["inputs"]
        if (
            result["expected_nonce_base64"] != context["expected_nonce_base64"]
            or result["evaluated_at"] != context["evaluation_unix_seconds"]
        ):
            raise ValueError("Result does not match the caller challenge context")
        if (
            result["policy_sha256"] != self.policy_sha256
            or result["report_sha256"]
            != hashlib.sha256(
                base64.b64decode(inputs["report"], validate=True)
            ).hexdigest()
        ):
            raise ValueError("Result does not match the caller inputs")
        for name, key in [
            ("amd_chain", "amd_chain_pem"),
            ("vcek", "vcek_der"),
            ("reference", "reference_json"),
        ]:
            if (
                result["input_sha256"][key]
                != hashlib.sha256(
                    base64.b64decode(inputs[name], validate=True)
                ).hexdigest()
            ):
                raise ValueError("Result input fingerprint mismatch")

    def consume(self, app, result):
        self.ensure_current(app, result)
        self.used = True
