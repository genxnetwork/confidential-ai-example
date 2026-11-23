"""Caller retrieval guards; mocked HTTP, no hardware assertions."""

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import httpx

from demo import admission, collection


class CollectionTests(unittest.TestCase):
    def setUp(self):
        collection._cache.clear()

    def test_transient_kds_retry_and_cache(self):
        url = collection.KDS + "/cert_chain"
        error = httpx.HTTPStatusError(
            "retry",
            request=httpx.Request("GET", url),
            response=httpx.Response(429, headers={"retry-after": "0"}),
        )
        with (
            patch.object(
                collection, "fetch", side_effect=[error, (b"raw signed data", {})]
            ) as fetch,
            patch.object(collection.time, "sleep"),
        ):
            self.assertEqual(collection.kds(url), b"raw signed data")
            self.assertEqual(collection.kds(url), b"raw signed data")
            self.assertEqual(fetch.call_count, 2)

    def test_retry_bound_and_excessive_retry_after(self):
        url = collection.KDS + "/cert_chain"
        for delay, count in [("0", 3), ("61", 1)]:
            error = httpx.HTTPStatusError(
                "retry",
                request=httpx.Request("GET", url),
                response=httpx.Response(503, headers={"retry-after": delay}),
            )
            with (
                patch.object(collection, "fetch", side_effect=error) as fetch,
                patch.object(collection.time, "sleep"),
            ):
                with self.assertRaises((httpx.HTTPStatusError, ValueError)):
                    collection.kds(url)
                self.assertEqual(fetch.call_count, count)

    def test_nonce_log_matches_report_request(self):
        nonce = bytes(range(32))
        encoded = base64.b64encode(nonce).decode()
        messages = []
        with (
            patch.object(collection.secrets, "token_bytes", return_value=nonce),
            patch.object(
                collection, "fetch", side_effect=RuntimeError("request intercepted")
            ) as fetch,
            self.assertRaisesRegex(RuntimeError, "request intercepted"),
        ):
            collection.collect_and_verify(
                {"origin": "https://example.test"}, progress=messages.append
            )
        self.assertEqual(fetch.call_args.args[0], "https://example.test/tee-report")
        self.assertEqual(fetch.call_args.kwargs["body"], {"nonce": encoded})
        self.assertTrue(
            any(
                "sending nonce in JSON body" in message and encoded in message
                for message in messages
            )
        )

    def test_collects_pinned_inputs_before_local_verification(self):
        nonce = bytes(range(32))
        app = {
            "origin": "https://example.test",
            "verifier_bytes": b"policy",
            "verifier": {
                "platform": {"product": "Genoa"},
                "reference": {
                    "repository": "org/repo",
                    "commit": "a" * 40,
                    "path": "values.json",
                },
            },
        }
        requirements = {
            "product": "Genoa",
            "chip_id": "b" * 128,
            "tcb": [1, 2, 3, 4],
        }

        def fetch_input(url, **kwargs):
            if url == "https://example.test/tee-report":
                return b"report", {"cache-control": "no-store"}
            self.assertIn("/repos/org/repo/contents/values.json?ref=", url)
            return b"reference", {}

        with (
            patch.object(collection.secrets, "token_bytes", return_value=nonce),
            patch.object(collection, "fetch", side_effect=fetch_input) as fetch,
            patch.object(collection, "kds", side_effect=[b"chain", b"vcek"]) as kds,
            patch.object(
                collection.confido_verifier,
                "inspect_requirements",
                return_value=requirements,
            ),
            patch.object(
                collection.confido_verifier,
                "verify",
                return_value={"status": "verified"},
            ) as verify,
        ):
            run = collection.collect_and_verify(app)

        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(kds.call_count, 2)
        verify.assert_called_once_with(
            b"report",
            b"chain",
            b"vcek",
            b"reference",
            b"policy",
            nonce,
            ANY,
        )
        self.assertEqual(run.archive["mode"], "live_collection")
        self.assertEqual(run.archive["origin"], app["origin"])
        self.assertEqual(
            run.archive["context"]["expected_nonce_base64"],
            base64.b64encode(nonce).decode(),
        )

    def test_rejects_product_mismatch_before_endorsement_retrieval(self):
        app = {"verifier": {"platform": {"product": "Genoa"}}}
        with (
            patch.object(
                collection.confido_verifier,
                "inspect_requirements",
                return_value={
                    "product": "Milan",
                    "chip_id": "b" * 128,
                    "tcb": [1, 2, 3, 4],
                },
            ),
            self.assertRaisesRegex(ValueError, "Unsupported KDS selector"),
        ):
            collection.kds_selectors(b"synthetic report", app)

    def test_evidence_failure_never_constructs_transport(self):
        with patch.object(admission, "Session") as session:
            with self.assertRaises(ValueError):
                admission.authenticate(
                    {}, {"scope": "evidence_only", "status": "policy_mismatch"}
                )
            session.assert_not_called()

    def test_peer_probe_uses_direct_endpoint_without_credentials(self):
        app = {"origin": "https://example.test"}
        result = {
            "scope": "evidence_only",
            "status": "verified",
            "verified_artifacts": {
                "certificate_der_base64": base64.b64encode(b"cert").decode()
            },
        }
        run = Mock()
        with patch.object(admission, "Session") as factory:
            factory.return_value.request.return_value = (204, [], b"")
            admission.authenticate(app, result, run=run)
            factory.assert_called_once_with(app["origin"], b"cert")
            factory.return_value.request.assert_called_once_with(
                "HEAD", "https://example.test/tee-report", [], b""
            )
            factory.return_value.request.return_value = (405, [], b"")
            with self.assertRaisesRegex(ValueError, "endpoint unavailable"):
                admission.authenticate(app, result, run=run)

    def test_policy_cannot_escape_local_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "origin": "https://example.test",
                        "verifier_policy": "../outside.json",
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "local"):
                collection.load_policy(path)
