"""Application decisions remain separate from Confido client appraisal."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from demo import admission

SPEC = importlib.util.spec_from_file_location(
    "chat_demo", Path(__file__).resolve().parents[1] / "confai-promter.py"
)
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.policy = demo.load_policy("match")
        self.record = {
            "checks": [],
            "status": "policy_mismatch",
            "reason": "measurement_mismatch",
            "coverage": {"ima_entries": 47},
            "scope": "evidence_only",
            "report_sha256": "0" * 64,
            "policy_sha256": hashlib.sha256(self.policy["verifier_bytes"]).hexdigest(),
        }

    def attempt(self, record):
        attempt = Mock()
        attempt.result = record
        attempt.archive = {
            "origin": self.policy["origin"] + "/",
            "inputs": {"report": "e30=", "reference": "e30="},
        }
        return attempt

    def run_setup(self, answer, record=None, *, peer_error=None):
        record = record or self.record
        attempt = self.attempt(record)
        with (
            tempfile.TemporaryDirectory() as path,
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo, "describe_verification"),
            patch.object(demo.confido_client, "appraise", return_value=attempt) as appraise,
            patch.object(
                demo.admission,
                "authenticate",
                side_effect=peer_error,
                return_value=Mock(),
            ) as authenticate,
            patch.object(demo, "ScopedTransport", return_value=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={})
            )),
            patch.object(demo.identity, "sign_in", return_value="user-token") as sign_in,
            patch.object(demo, "new_bundle_path", return_value=Path(path) / "run.json"),
            patch.object(demo.openai, "OpenAI") as app,
            patch("builtins.input", return_value=answer),
            patch("builtins.print"),
        ):
            demo.setup_client("match")
            return appraise.call_count, authenticate.call_count, app.call_count, sign_in.call_count

    def test_decline_does_not_sign_in_or_appraise(self):
        self.assertEqual(self.run_setup("n"), (0, 0, 0, 0))

    def test_rejected_evidence_never_opens_chat(self):
        self.assertEqual(self.run_setup("y"), (1, 0, 0, 1))

    def test_match_opens_chat_only_after_peer_authentication(self):
        self.record.update(status="verified", reason="reference_match")
        self.assertEqual(self.run_setup(""), (1, 1, 1, 1))

    def test_sign_in_failure_withholds_evidence_and_chat(self):
        with (
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo.identity, "sign_in", side_effect=RuntimeError("unavailable")),
            patch.object(demo.confido_client, "appraise") as appraise,
            patch.object(demo.openai, "OpenAI") as app,
            patch("builtins.input", return_value=""),
            patch("builtins.print"),
        ):
            self.assertIsNone(demo.setup_client("match"))
            appraise.assert_not_called()
            app.assert_not_called()

    def test_peer_or_deadline_failure_withholds_chat(self):
        self.record.update(status="verified", reason="reference_match")
        for reason in ("wrong peer", "Challenge deadline expired"):
            self.assertEqual(
                self.run_setup("y", peer_error=ValueError(reason)),
                (1, 1, 0, 1),
            )

    def test_runtime_failure_prevents_collection(self):
        with (
            patch.object(demo, "ensure_runtime", side_effect=RuntimeError("stale binary")),
            patch.object(demo.confido_client, "appraise") as appraise,
        ):
            with self.assertRaisesRegex(RuntimeError, "stale binary"):
                demo.setup_client("match")
            appraise.assert_not_called()

    def test_admission_rejects_changed_policy_result_or_origin(self):
        self.record.update(status="verified", reason="reference_match")
        attempt = self.attempt(self.record)
        admission.authenticate(self.policy, self.record, attempt=attempt)
        attempt.authenticate_peer.assert_called_once_with()

        for changed_app, changed_result, changed_origin in (
            (dict(self.policy, verifier_bytes=b"changed"), self.record, self.policy["origin"]),
            (self.policy, dict(self.record, reason="altered"), self.policy["origin"]),
            (self.policy, self.record, "https://other.test"),
        ):
            candidate = self.attempt(self.record)
            candidate.archive["origin"] = changed_origin
            with self.assertRaises(ValueError):
                admission.authenticate(changed_app, changed_result, attempt=candidate)
            candidate.authenticate_peer.assert_not_called()

    def test_sdk_makes_one_request_through_admitted_chat_transport(self):
        forwarded = []

        def respond(request):
            forwarded.append(request)
            return httpx.Response(200, json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": demo.CHAT_MODEL,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }],
            })

        http = httpx.Client(
            transport=demo.ChatTransport(httpx.MockTransport(respond), "user-token"),
            follow_redirects=False,
            trust_env=False,
        )
        app = demo.openai.OpenAI(
            api_key="user-token",
            base_url="https://example.test/v1",
            http_client=http,
            max_retries=0,
        )
        self.assertEqual(len(forwarded), 0)
        response = app.chat.completions.create(
            model=demo.CHAT_MODEL,
            messages=[{"role": "user", "content": "synthetic request"}],
        )
        self.assertEqual(response.choices[0].message.content, "ok")
        self.assertEqual(len(forwarded), 1)
        self.assertEqual(forwarded[0].url.path, "/v1/chat/completions")
        self.assertEqual(forwarded[0].headers["authorization"], "Bearer user-token")
        app.close()


if __name__ == "__main__":
    unittest.main()
