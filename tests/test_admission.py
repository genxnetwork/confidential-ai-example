"""Client orchestration tests: mocks are not presented as hardware validation."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "chat_demo", Path(__file__).resolve().parents[1] / "confai-promter.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


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
        }

    def live_run(self, record):
        return Mock(result=record, archive={"inputs": {"report": "e30="}}, timings={})

    def run_setup(self, answer, record=None):
        record = record or self.record
        session = Mock(result_json=json.dumps(record))
        with (
            tempfile.TemporaryDirectory() as path,
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo, "describe_verification"),
            patch.object(
                demo.collection,
                "collect_and_verify",
                return_value=self.live_run(record),
            ) as connect,
            patch.object(demo.admission, "authenticate", return_value=session),
            patch.object(demo, "new_bundle_path", return_value=Path(path) / "run.json"),
            patch.object(
                demo, "read_credentials", return_value=("test", "sentinel")
            ) as credentials,
            patch.object(demo.openai, "OpenAI") as app,
            patch("builtins.input", return_value=answer),
            patch("builtins.print"),
        ):
            demo.setup_client("match")
            return connect.call_count, credentials.call_count, app.call_count

    def test_decline_never_appraises_or_reads_credentials(self):
        self.assertEqual(self.run_setup("n"), (0, 0, 0))

    def test_each_failure_withholds_application_and_credentials(self):
        for reason in [
            "measurement_mismatch",
            "quote_binding_invalid",
            "https_authentication_failed",
            "collection_unavailable",
        ]:
            self.record["reason"] = reason
            self.assertEqual(self.run_setup("y"), (1, 0, 0))

    def test_enter_accepts_and_credentials_follow_admission(self):
        self.record.update(status="verified", reason="reference_match")
        self.assertEqual(self.run_setup(""), (1, 1, 1))

    def test_peer_failure_withholds_credentials(self):
        self.record.update(status="verified", reason="reference_match")
        with (
            tempfile.TemporaryDirectory() as path,
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo, "describe_verification"),
            patch.object(
                demo.collection,
                "collect_and_verify",
                return_value=self.live_run(self.record),
            ),
            patch.object(
                demo.admission, "authenticate", side_effect=ValueError("wrong peer")
            ),
            patch.object(demo, "new_bundle_path", return_value=Path(path) / "run.json"),
            patch.object(demo, "read_credentials") as credentials,
            patch("builtins.input", return_value=""),
            patch("builtins.print"),
        ):
            self.assertIsNone(demo.setup_client("match"))
            credentials.assert_not_called()
            self.assertFalse(
                json.loads((Path(path) / "run.decision.json").read_text())[
                    "application_admitted"
                ]
            )

    def test_runtime_failure_prevents_collection(self):
        with (
            patch.object(
                demo, "ensure_runtime", side_effect=RuntimeError("stale binary")
            ),
            patch.object(demo.collection, "collect_and_verify") as collect,
        ):
            with self.assertRaisesRegex(RuntimeError, "stale binary"):
                demo.setup_client("match")
            collect.assert_not_called()

    def test_expiry_after_rendering_withholds_credentials(self):
        self.record.update(status="verified", reason="reference_match")
        run = self.live_run(self.record)
        run.consume.side_effect = ValueError("Challenge deadline expired")
        with patch.object(self, "live_run", return_value=run):
            self.assertEqual(self.run_setup(""), (1, 0, 0))

    def test_sdk_uses_scoped_transport_without_hidden_requests(self):
        session = Mock()
        session.request.return_value = (
            200,
            [("content-type", "application/json")],
            json.dumps(
                {
                    "id": "test",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "llama-default",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ],
                }
            ).encode(),
        )
        http = demo.httpx.Client(
            transport=demo.AppraisedTransport(session),
            auth=("test", "sentinel"),
            follow_redirects=False,
        )
        app = demo.openai.OpenAI(
            api_key="null",
            base_url="https://localhost/v1",
            http_client=http,
            max_retries=0,
        )
        self.assertEqual(session.request.call_count, 0)
        response = app.chat.completions.create(
            model="llama-default",
            messages=[{"role": "user", "content": "synthetic transport test"}],
        )
        self.assertEqual(response.choices[0].message.content, "ok")
        self.assertEqual(session.request.call_count, 1)
        self.assertEqual(
            session.request.call_args.args[1], "https://localhost/v1/chat/completions"
        )
        app.close()


if __name__ == "__main__":
    unittest.main()
