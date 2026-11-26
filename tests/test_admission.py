"""Application decisions remain separate from Confido client appraisal."""

import hashlib
import importlib.util
import json
import contextlib
import io
import subprocess
import sys
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


def synthetic_session(token, _expires_at, label):
    """Provide user credentials without replacing the admission or request path."""
    auth = Mock(access_token=token, identity=label)
    auth.token.return_value = token
    return auth


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
            patch.object(demo, "print_verification"),
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
            patch.object(demo, "new_bundle_path", return_value=Path(path) / "run.json"),
            patch.object(demo.openai, "OpenAI") as app,
            patch("builtins.input", return_value=answer),
            patch("builtins.print"),
        ):
            demo.setup_client("match", synthetic_session("user-token", float("inf"), "Test user"))
            return appraise.call_count, authenticate.call_count, app.call_count

    def test_decline_does_not_appraise(self):
        self.assertEqual(self.run_setup("n"), (0, 0, 0))

    def test_rejected_evidence_never_opens_chat(self):
        self.assertEqual(self.run_setup("y"), (1, 0, 0))

    def test_match_opens_chat_only_after_peer_authentication(self):
        self.record.update(status="verified", reason="reference_match")
        self.assertEqual(self.run_setup(""), (1, 1, 1))

    def test_sign_in_failure_withholds_evidence_and_chat(self):
        with (
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo.identity, "authenticate", side_effect=RuntimeError("unavailable")),
            patch.object(demo.confido_client, "appraise") as appraise,
            patch.object(demo.openai, "OpenAI") as app,
            patch("builtins.input") as prompt,
            patch("builtins.print"),
        ):
            self.assertEqual(demo.main(), 1)
            prompt.assert_not_called()
            appraise.assert_not_called()
            app.assert_not_called()

    def test_peer_or_deadline_failure_withholds_chat(self):
        self.record.update(status="verified", reason="reference_match")
        for reason in ("wrong peer", "Challenge deadline expired"):
            self.assertEqual(
                self.run_setup("y", peer_error=ValueError(reason)),
                (1, 1, 0),
            )

    def test_runtime_failure_prevents_collection(self):
        with (
            patch.object(demo, "ensure_runtime", side_effect=RuntimeError("stale binary")),
            patch.object(demo.confido_client, "appraise") as appraise,
        ):
            with self.assertRaisesRegex(RuntimeError, "stale binary"):
                demo.setup_client("match", synthetic_session("user-token", float("inf"), "Test user"))
            appraise.assert_not_called()

    def test_sign_in_precedes_endpoint_selection_and_is_reused(self):
        auth = synthetic_session("user-token", float("inf"), "Test user")
        events = []
        answers = iter(["1", "2", "0"])
        def prompt(_text):
            events.append("endpoint")
            return next(answers)
        with (
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo.identity, "authenticate", side_effect=lambda: events.append("auth") or auth) as login,
            patch.object(demo, "setup_client", return_value=None) as setup,
            patch("builtins.input", side_effect=prompt),
            patch("builtins.print"),
        ):
            demo.main()
        login.assert_called_once()
        self.assertEqual(events[0], "auth")
        self.assertEqual(setup.call_args_list, [unittest.mock.call("match", auth, runtime={}), unittest.mock.call("mismatch", auth, runtime={})])

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

        auth = synthetic_session("previous-token", float("inf"), "Test user")
        http = httpx.Client(
            transport=demo.ChatTransport(httpx.MockTransport(respond), lambda: auth.access_token),
            follow_redirects=False,
            trust_env=False,
        )
        app = demo.openai.OpenAI(
            api_key=auth.token,
            base_url="https://example.test/v1",
            http_client=http,
            max_retries=0,
        )
        self.assertEqual(len(forwarded), 0)
        auth.access_token = "user-token"
        auth.token.return_value = "user-token"
        response = app.chat.completions.create(
            model=demo.CHAT_MODEL,
            messages=[{"role": "user", "content": "synthetic request"}],
        )
        self.assertEqual(response.choices[0].message.content, "ok")
        self.assertEqual(len(forwarded), 1)
        self.assertEqual(forwarded[0].url.path, "/v1/chat/completions")
        self.assertEqual(forwarded[0].headers["authorization"], "Bearer user-token")
        app.close()

    def test_flint_token_is_forwarded_only_after_appraisal_and_peer_verification(self):
        for scenario in ("match", "mismatch", "wrong-peer"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                events = []
                record = dict(self.record)
                if scenario != "mismatch":
                    record.update(status="verified", reason="reference_match")
                attempt = self.attempt(record)
                def peer():
                    events.append("peer")
                    if scenario == "wrong-peer":
                        raise ValueError("Wrong HTTPS peer")
                    return Mock()
                attempt.authenticate_peer.side_effect = peer
                msal_app = Mock()
                msal_app.token_cache = demo.identity.msal.SerializableTokenCache()
                def acquire(*args, **kwargs):
                    events.append("token")
                    return {"access_token": "synthetic-flint-token"}
                msal_app.acquire_token_silent_with_error.side_effect = acquire
                auth = demo.identity.Session(msal_app, {"username": "user@example.test"})
                def respond(request):
                    events.append("request")
                    self.assertEqual(request.headers["authorization"], "Bearer synthetic-flint-token")
                    return httpx.Response(200, json={"object": "list", "data": []})
                def appraise(*args):
                    events.append("appraisal")
                    return attempt
                with (patch.object(demo, "ensure_runtime", return_value={}),
                      patch.object(demo, "print_verification"),
                      patch.object(demo.identity, "cache_path", return_value=Path(directory) / "identity-cache.json"),
                      patch.object(demo.confido_client, "appraise", side_effect=appraise),
                      patch.object(demo, "ScopedTransport", return_value=httpx.MockTransport(respond)),
                      patch.object(demo, "new_bundle_path", return_value=Path(directory) / "run.json"),
                      patch("builtins.input", return_value="y"), patch("builtins.print")):
                    client = demo.setup_client("match", auth)
                    if scenario == "match":
                        self.assertEqual(events, ["appraisal", "peer"])
                        with client:
                            client.models.list()
                        self.assertEqual(events, ["appraisal", "peer", "token", "request"])
                    else:
                        self.assertIsNone(client)
                        msal_app.acquire_token_silent_with_error.assert_not_called()
                        self.assertNotIn("request", events)

    def test_chat_does_not_print_echoed_authorization_or_error_cause(self):
        secret = "synthetic-private-marker"
        responses = [
            httpx.Response(500, json={"error": {"message": secret}}),
            httpx.ConnectError(secret),
        ]
        for response in responses:
            def respond(request):
                self.assertEqual(request.headers["authorization"], f"Bearer {secret}")
                if isinstance(response, Exception):
                    raise response
                return response
            with self.subTest(response=type(response).__name__), demo.openai.OpenAI(
                api_key=secret,
                base_url="https://example.test/v1",
                max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond), trust_env=False),
            ) as client:
                output = io.StringIO()
                with patch("builtins.input", side_effect=["synthetic", "quit"]), contextlib.redirect_stdout(output):
                    demo.chat_loop(client)
                self.assertNotIn(secret, output.getvalue())
                self.assertIn("HTTP 500" if isinstance(response, httpx.Response) else "Connection failed", output.getvalue())

    def test_temporary_renewal_failure_during_chat_does_not_log_off(self):
        auth = synthetic_session("synthetic-access", 0, "Test user")
        auth.token.side_effect = demo.identity.SessionUnavailable("Session could not be renewed")
        forwarded = Mock(return_value=httpx.Response(200, json={}))
        client = demo.openai.OpenAI(
            api_key=auth.token,
            base_url="https://example.test/v1",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(forwarded), trust_env=False),
        )
        with (
            patch.object(demo, "ensure_runtime", return_value={}),
            patch.object(demo.identity, "authenticate", return_value=auth) as login,
            patch.object(demo.identity, "logoff") as logoff,
            patch.object(demo, "setup_client", return_value=client),
            patch("builtins.input", side_effect=["1", "synthetic", "quit", "0"]),
            patch("builtins.print"),
        ):
            demo.main()
        login.assert_called_once()
        logoff.assert_not_called()
        forwarded.assert_not_called()

    def test_api_401_preserves_identity_without_replaying_or_interactive_login(self):
        auth = synthetic_session("synthetic-token", float("inf"), "Test user")
        forwarded = Mock(return_value=httpx.Response(
            401, json={"error": {"message": "synthetic-private-server-body"}}))
        client = demo.openai.OpenAI(
            api_key=auth.token, base_url="https://example.test/v1", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(forwarded), trust_env=False),
        )
        output = io.StringIO()
        with (patch.object(demo, "ensure_runtime", return_value={}),
              patch.object(demo.identity, "authenticate", return_value=auth) as login,
              patch.object(demo.identity, "logoff") as logoff,
              patch.object(demo, "setup_client", return_value=client),
              patch("builtins.input", side_effect=["1", "synthetic prompt", "0"]),
              contextlib.redirect_stdout(output)):
            self.assertEqual(demo.main(), 0)
        login.assert_called_once()
        logoff.assert_not_called()
        forwarded.assert_called_once()
        self.assertIn("Saved sign-in kept", output.getvalue())
        self.assertNotIn("Sign-in expired", output.getvalue())
        self.assertNotIn("synthetic-private-server-body", output.getvalue())

    def test_chat_bounds_generated_tokens_and_shows_native_failure_safely(self):
        requests = []
        def respond(request):
            requests.append(json.loads(request.content))
            raise RuntimeError("synthetic-private-native-error")
        with demo.openai.OpenAI(
            api_key="synthetic-token", base_url="https://example.test/v1", max_retries=0,
            http_client=httpx.Client(transport=demo.ChatTransport(
                httpx.MockTransport(respond), "synthetic-token"), trust_env=False),
        ) as client:
            output = io.StringIO()
            with patch("builtins.input", side_effect=["how are you?", "quit"]), contextlib.redirect_stdout(output):
                demo.chat_loop(client)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["model"], "llama-default")
        self.assertEqual(requests[0]["max_tokens"], 256)
        self.assertIn("Generating", output.getvalue())
        self.assertIn("Connection failed or timed out", output.getvalue())
        self.assertNotIn("RuntimeError", output.getvalue())
        self.assertNotIn("synthetic-private-native-error", output.getvalue())

    def test_failed_logoff_returns_safe_failure_without_starting_another_login(self):
        auth = synthetic_session("synthetic-access", float("inf"), "user")
        errors = io.StringIO()
        with (patch.object(demo, "ensure_runtime", return_value={}),
              patch.object(demo.identity, "authenticate", return_value=auth) as login,
              patch.object(demo, "setup_client", return_value=Mock()),
              patch.object(demo, "chat_loop", side_effect=demo.identity.AuthenticationRequired()),
              patch.object(demo.identity, "logoff", side_effect=demo.identity.SessionUnavailable("synthetic-private-marker")),
              patch("builtins.input", return_value="1"), patch("builtins.print"),
              contextlib.redirect_stderr(errors)):
            self.assertEqual(demo.main(), 1)
        login.assert_called_once()
        self.assertNotIn("synthetic-private-marker", errors.getvalue())

    def test_fatal_startup_errors_return_failure_exit_status(self):
        for target in ("demo.runtime.ensure_runtime", "demo.identity.authenticate"):
            code = (
                "import runpy\nfrom unittest.mock import patch\n"
                "with patch('demo.runtime.ensure_runtime', return_value={}), "
                f"patch({target!r}, side_effect=RuntimeError('synthetic failure')):\n"
                "    runpy.run_path('confai-promter.py', run_name='__main__')\n"
            )
            with self.subTest(target=target):
                result = subprocess.run(
                    [sys.executable, "-c", code], cwd=Path(SPEC.origin).parent,
                    text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("failed" if target.endswith("authenticate") else "incompatible", result.stderr)


if __name__ == "__main__":
    unittest.main()
