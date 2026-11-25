"""Exercise real MSAL acquisition and persisted session recovery at its HTTP boundary."""

import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from demo import identity
from identity_provider import IdentityProvider


class IdentityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "application"
        self.provider = IdentityProvider()
        for patcher in (
            patch.object(identity, "state_directory", return_value=self.root),
            patch("requests.Session.get", side_effect=self.provider.get),
            patch("requests.Session.post", side_effect=self.provider.post),
            patch.object(identity, "receive_response", side_effect=lambda url, _state: self.provider.capture_authorization(url)),
            patch("builtins.print"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def sign_in(self):
        with patch("builtins.input", return_value="y"):
            return identity.authenticate()

    def recover(self):
        with patch("builtins.input", return_value="y"):
            return identity.authenticate()

    def test_msal_owns_pkce_scopes_and_private_cache_recovery(self):
        first = self.sign_in()
        self.assertEqual(first.access_token, "synthetic-access-1")
        self.assertEqual(first.identity, "user@example.test")
        self.assertNotIn(first.access_token, repr(first))
        path = identity.cache_path()
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(set(self.provider.query["scope"][0].split()),
                         set(identity.SCOPES + ["openid", "profile", "offline_access"]))
        self.assertEqual(self.provider.query["response_mode"], ["query"])
        with patch.object(identity, "receive_response") as browser:
            recovered = self.recover()
        browser.assert_not_called()
        self.assertEqual(recovered.token(), first.access_token)
        self.assertEqual(len(self.provider.posts), 1)
        self.assertIsNot(first.app, recovered.app)

    def test_expired_token_renews_through_msal_after_restart(self):
        self.provider.lifetime = -3600
        self.sign_in()
        self.provider.lifetime = 3600
        recovered = self.recover()
        self.assertEqual(recovered.access_token, "synthetic-access-2")
        self.assertEqual(self.provider.posts[-1]["grant_type"], "refresh_token")
        self.assertEqual(self.provider.posts[-1]["refresh_token"], "synthetic-refresh-1")
        self.assertEqual(self.recover().token(), "synthetic-access-2")
        self.assertEqual(len(self.provider.posts), 2)

    def test_session_lasts_over_fifteen_minutes_with_silent_refresh(self):
        started = 1800000000
        now = [started]
        self.provider.lifetime = 300
        with (patch("time.time", side_effect=lambda: now[0]),
              patch.object(identity, "receive_response", side_effect=lambda url, _state:
                           self.provider.capture_authorization(url)) as browser):
            self.sign_in()
            for elapsed in (60, 6 * 60, 15 * 60, 20 * 60):
                now[0] = started + elapsed
                self.assertTrue(self.recover().token())
            browser.assert_called_once()
        self.assertGreater(len(self.provider.posts), 1)
        self.assertEqual(self.provider.posts[0]["grant_type"], "authorization_code")
        self.assertTrue(all(p["grant_type"] == "refresh_token" for p in self.provider.posts[1:]))

    def test_temporary_failures_preserve_cache_and_do_not_open_browser(self):
        self.provider.lifetime = -3600
        self.sign_in()
        original = identity.cache_path().read_bytes()
        for failure in (
            (503, {"error": "temporarily_unavailable", "error_description": "synthetic-private-marker"}),
            (400, {"error": "invalid_client"}),
            (200, {}),
            requests.ConnectTimeout("synthetic-private-marker"),
        ):
            self.provider.failure = failure
            with (self.subTest(failure=type(failure).__name__),
                  patch.object(identity, "receive_response") as browser,
                  self.assertRaises(identity.SessionUnavailable) as caught):
                self.recover()
            self.assertNotIn("synthetic-private-marker", str(caught.exception))
            self.assertEqual(identity.cache_path().read_bytes(), original)
            browser.assert_not_called()
        self.provider.failure = None
        self.provider.lifetime = 3600
        self.assertEqual(self.recover().token(), "synthetic-access-2")

    def test_confirmed_rejection_requires_explicit_new_login(self):
        self.provider.lifetime = -3600
        self.sign_in()
        self.provider.failure = (400, {"error": "invalid_grant"})
        with (patch("builtins.input", side_effect=["y", "n"]),
              patch.object(identity, "receive_response") as browser):
            self.assertIsNone(identity.authenticate())
        browser.assert_not_called()
        self.assertEqual(identity.create_application().get_accounts(), [])

    def test_local_logoff_clears_only_application_cache(self):
        session = self.sign_in()
        unrelated = self.root / "other-client.json"
        unrelated.write_text("unrelated")
        identity.logoff(session)
        self.assertEqual(identity.create_application().get_accounts(), [])
        self.assertEqual(unrelated.read_text(), "unrelated")

    def test_legacy_session_requires_login_and_is_removed_only_after_success(self):
        self.root.mkdir()
        legacy = self.root / "session.json"
        legacy.write_text('{"access_token":"synthetic-legacy"}')
        with patch("builtins.input", return_value="n"):
            self.assertIsNone(identity.authenticate())
        self.assertTrue(legacy.exists())
        self.sign_in()
        self.assertFalse(legacy.exists())
        self.assertNotIn("synthetic-legacy", identity.cache_path().read_text())

    def test_corrupt_or_public_cache_is_preserved_and_rejected(self):
        self.root.mkdir()
        path = identity.cache_path()
        for content, mode in (("invalid cache", 0o600), ("[]", 0o600), ("invalid cache", 0o644)):
            path.write_text(content)
            os.chmod(path, mode)
            with self.subTest(content=content, mode=mode), self.assertRaises(identity.SessionUnavailable):
                self.recover()
            self.assertEqual(path.read_text(), content)

    def test_cache_partition_changes_with_client_authority_or_scopes(self):
        original = identity.cache_path()
        for name, value in (("CLIENT_ID", "other-client"), ("AUTHORITY", identity.AUTHORITY + "/other"),
                            ("SCOPES", ["api://other/read"])):
            with self.subTest(name=name), patch.object(identity, name, value):
                self.assertNotEqual(identity.cache_path(), original)

    def test_atomic_storage_failure_keeps_previous_cache(self):
        self.sign_in()
        path = identity.cache_path()
        before = path.read_bytes()
        with patch("pathlib.Path.replace", side_effect=OSError("synthetic-private-marker")):
            with self.assertRaises(OSError):
                identity.PrivateFilePersistence(str(path)).save("replacement")
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(path.parent.iterdir()), [path])

    def test_account_selection_is_explicit_and_display_is_safe(self):
        accounts = [{"username": "first\x1b\n"}, {"username": "second"}]
        with patch("builtins.input", side_effect=["0", "2"]):
            self.assertIs(identity.choose_account(accounts), accounts[1])
        self.assertEqual(identity.display_identity(accounts[0]), "first")

    def test_failed_msal_state_or_nonce_validation_never_commits_credentials(self):
        for failure in ("state", "nonce"):
            with self.subTest(failure=failure):
                self.provider.nonce_override = "wrong-nonce" if failure == "nonce" else None
                def response(url, _state):
                    result = self.provider.capture_authorization(url)
                    if failure == "state":
                        result["state"] = "wrong-state"
                    return result
                with patch.object(identity, "receive_response", side_effect=response):
                    with self.assertRaises(identity.SessionUnavailable) as caught:
                        self.sign_in()
                self.assertNotIn("wrong-nonce", str(caught.exception))
                self.assertFalse(identity.cache_path().exists())
                self.assertEqual(identity.create_application().get_accounts(), [])
                if failure == "state":
                    self.assertEqual(self.provider.posts, [])

    def test_stale_clients_observe_refresh_and_logoff_in_both_orders(self):
        self.provider.lifetime = -3600
        first = self.sign_in()
        second_app = identity.create_application()
        second = identity.Session(second_app, second_app.get_accounts()[0])
        self.provider.lifetime = 3600
        self.assertEqual(first.token(), "synthetic-access-2")
        identity.logoff(second)
        self.assertEqual(identity.create_application().get_accounts(), [])
        before = len(self.provider.posts)
        with self.assertRaises(identity.SessionUnavailable):
            first.token()
        self.assertEqual(len(self.provider.posts), before)
        self.assertEqual(identity.create_application().get_accounts(), [])

        first = self.sign_in()
        second_app = identity.create_application()
        second = identity.Session(second_app, second_app.get_accounts()[0])
        identity.logoff(second)
        before = len(self.provider.posts)
        with self.assertRaises(identity.SessionUnavailable):
            first.token()
        self.assertEqual(len(self.provider.posts), before)
        self.assertEqual(identity.create_application().get_accounts(), [])

    def test_refresh_and_logoff_serialize_in_both_competing_orders(self):
        for first_operation in ("refresh", "logoff"):
            with self.subTest(first_operation=first_operation):
                self.provider.lifetime = -3600
                first = self.sign_in()
                other_app = identity.create_application()
                second = identity.Session(other_app, other_app.get_accounts()[0])
                self.provider.lifetime = 3600
                entered = threading.Event()
                waiting = threading.Event()
                release = threading.Event()
                secondary_thread = [None]
                original_lock = identity.CrossPlatLock
                original_post = self.provider.post
                original_remove = first.app.remove_account
                before = len(self.provider.posts)

                @contextmanager
                def observe_lock(path):
                    if threading.get_ident() == secondary_thread[0]:
                        waiting.set()
                    with original_lock(path):
                        yield

                def pause_first():
                    entered.set()
                    if not release.wait(3):
                        raise AssertionError("Test did not release the first operation")

                def token_post(*args, **kwargs):
                    if first_operation == "refresh":
                        pause_first()
                    return original_post(*args, **kwargs)

                def remove_account(account):
                    pause_first()
                    return original_remove(account)

                def competing_operation():
                    secondary_thread[0] = threading.get_ident()
                    if first_operation == "refresh":
                        identity.logoff(second)
                    else:
                        with self.assertRaises(identity.SessionUnavailable):
                            second.token()

                with (patch.object(identity, "CrossPlatLock", side_effect=observe_lock),
                      patch("requests.Session.post", side_effect=token_post),
                      patch.object(first.app, "remove_account", side_effect=remove_account),
                      ThreadPoolExecutor(max_workers=2) as executor):
                    operation = first.token if first_operation == "refresh" else lambda: identity.logoff(first)
                    first_future = executor.submit(operation)
                    try:
                        self.assertTrue(entered.wait(2))
                        second_future = executor.submit(competing_operation)
                        self.assertTrue(waiting.wait(2))
                    finally:
                        release.set()
                    first_future.result(timeout=2)
                    second_future.result(timeout=2)
                self.assertEqual(identity.create_application().get_accounts(), [])
                self.assertEqual(len(self.provider.posts) - before,
                                 1 if first_operation == "refresh" else 0)

    def test_incomplete_login_cannot_be_attached_to_a_previous_account(self):
        self.sign_in()
        before = identity.cache_path().read_bytes()
        self.provider.omit_id_token = True
        with self.assertRaises(identity.SessionUnavailable):
            identity.sign_in(identity.create_application())
        self.assertEqual(identity.cache_path().read_bytes(), before)
