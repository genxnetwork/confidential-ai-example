"""Client orchestration tests: mocks are not presented as hardware validation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location("demo", Path(__file__).resolve().parents[1] / "confai-promter.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.policy = demo.load_policy("match")
        self.preview = {"id": self.policy["service_id"], "teeReport": {"profile": "azure-snp-vtpm-ima/1", "wireVersion": 1}}
        self.record = {"checks": [], "status": "policy_mismatch", "reason": "measurement_mismatch",
                       "coverage": {"ima_entries": 47}, "application_admitted": False}

    def run_setup(self, answer, record=None):
        record = record or self.record
        session = Mock(result_json=json.dumps(record))
        with tempfile.TemporaryDirectory() as path, \
             patch.object(demo.confido, "__version__", "0.3.0"), \
             patch.object(demo.confido, "discover_py", return_value=json.dumps(self.preview)), \
             patch.object(demo.confido, "connect_py", return_value=session) as connect, \
             patch.object(demo, "new_bundle_path", return_value=Path(path)/"run.json"), \
             patch.object(demo, "read_credentials", return_value=("test", "sentinel")) as credentials, \
             patch.object(demo.openai, "OpenAI") as app, \
             patch("builtins.input", return_value=answer), patch("builtins.print"):
            demo.setup_client("match")
            return connect.call_count, credentials.call_count, app.call_count

    def test_decline_never_appraises_or_reads_credentials(self):
        self.assertEqual(self.run_setup("n"), (0, 0, 0))

    def test_each_failure_withholds_application_and_credentials(self):
        for reason in ["measurement_mismatch", "quote_binding_invalid", "https_authentication_failed", "collection_unavailable", "unsupported_discovery"]:
            self.record["reason"] = reason
            self.assertEqual(self.run_setup("y"), (1, 0, 0))

    def test_enter_accepts_and_credentials_follow_admission(self):
        self.record.update(status="passed", reason="reference_match", application_admitted=True)
        self.assertEqual(self.run_setup(""), (1, 1, 1))

    def test_old_advertisement_never_appraises(self):
        self.preview["teeReport"].pop("wireVersion")
        self.assertEqual(self.run_setup("y"), (0, 0, 0))

    def test_sdk_uses_scoped_transport_without_hidden_requests(self):
        session = Mock()
        session.request.return_value = (200, [("content-type", "application/json")], json.dumps({"id":"test","object":"chat.completion","created":0,"model":"llama-default","choices":[{"index":0,"message":{"role":"assistant","content":"ok"},"finish_reason":"stop"}]}).encode())
        http = demo.httpx.Client(transport=demo.AppraisedTransport(session), auth=("test","sentinel"), follow_redirects=False)
        app = demo.openai.OpenAI(api_key="null",base_url="https://localhost/v1",http_client=http,max_retries=0)
        self.assertEqual(session.request.call_count, 0)
        response = app.chat.completions.create(model="llama-default",messages=[{"role":"user","content":"synthetic transport test"}])
        self.assertEqual(response.choices[0].message.content,"ok")
        self.assertEqual(session.request.call_count,1)
        self.assertEqual(session.request.call_args.args[1],"https://localhost/v1/chat/completions")
        app.close()


if __name__ == "__main__":
    unittest.main()
