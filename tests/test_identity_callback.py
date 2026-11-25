"""Drive the real Docker callback receiver using local HTTP connections."""

import socket
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import Mock, patch

from demo import identity_callback as callback


class CallbackTests(unittest.TestCase):
    def run_callback(self, exercise, *, clock=None, handoff="", output=None):
        ready = threading.Event()
        accepted = threading.Event()
        context = {}
        original_server = callback.ThreadingHTTPServer

        class EphemeralServer(original_server):
            def __init__(self, address, handler):
                super().__init__(("127.0.0.1", 0), handler)
                context["address"] = self.server_address
                ready.set()

            def get_request(self):
                result = super().get_request()
                accepted.set()
                return result

        def show_url(_url):
            ready.set()

        with (patch.object(callback, "ThreadingHTTPServer", EphemeralServer),
              patch.object(callback, "show_authorization_url", side_effect=show_url),
              patch.object(callback, "time", clock or time),
              patch.dict(callback.os.environ, CONFIDO_BROWSER_HANDOFF=handoff),
              patch("builtins.print", output or Mock()),
              patch.object(callback, "BROWSER_FALLBACK_SECONDS", 1),
              patch.object(callback, "SIGN_IN_TIMEOUT", 3),
              ThreadPoolExecutor(max_workers=1) as executor):
            future = executor.submit(callback.receive_response, "https://identity.test/auth", "expected-state")
            try:
                if not ready.wait(2):
                    future.result(timeout=2)
                    self.fail("Callback receiver did not start")
                with socket.create_connection(context["address"], timeout=2) as stalled:
                    stalled.sendall(b"POST / HTTP/1.1\r\n")
                    self.assertTrue(accepted.wait(2))
                    exercise(context["address"], future)
            finally:
                if clock is not None:
                    clock.monotonic = lambda: float("inf")

    def post(self, address, body):
        connection = HTTPConnection(*address, timeout=2)
        try:
            connection.request("POST", "/", body, {"Content-Type": "application/x-www-form-urlencoded"})
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    def get(self, address, path):
        connection = HTTPConnection(*address, timeout=2)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            return response.status, response.getheader("Location")
        finally:
            connection.close()

    def test_host_browser_handoff_preserves_form_callback_and_hides_url(self):
        handoff = "synthetic-browser-launch-1234"
        output = Mock()
        def exercise(address, future):
            self.assertEqual(self.get(address, "/browser/wrong")[0], 400)
            self.assertEqual(self.get(address, "/browser/" + handoff + "/ready"), (200, None))
            self.assertEqual(self.get(address, "/browser/" + handoff),
                             (302, "https://identity.test/auth"))
            self.assertEqual(self.get(address, "/?code=ignored")[0], 400)
            self.assertFalse(future.done())
            self.assertEqual(self.post(address, "state=expected-state&code=synthetic"), 200)
            self.assertEqual(future.result(timeout=2)["code"], "synthetic")
        self.run_callback(exercise, handoff=handoff, output=output)
        self.assertNotIn("https://identity.test/auth", str(output.call_args_list))

    def test_missing_browser_navigation_prints_manual_url_without_cancelling_login(self):
        now = [0.0]
        shown = threading.Event()
        output = Mock(side_effect=lambda *args, **kwargs:
                      shown.set() if "https://identity.test/auth" in str(args) else None)
        def exercise(address, future):
            now[0] = 2.0
            self.assertEqual(self.get(address, "/browser/synthetic-browser-launch-1234/ready")[0], 200)
            self.assertTrue(shown.wait(2))
            self.assertEqual(self.post(address, "state=expected-state&code=synthetic"), 200)
            self.assertEqual(future.result(timeout=2)["code"], "synthetic")
        self.run_callback(exercise, handoff="synthetic-browser-launch-1234", output=output,
                          clock=SimpleNamespace(monotonic=lambda: now[0]))
        self.assertEqual(sum("https://identity.test/auth" in str(call) for call in output.call_args_list), 1)

    def test_native_browser_success_and_failure_output(self):
        for result in (True, False, OSError("no desktop")):
            with (self.subTest(result=result), patch("builtins.print") as output,
                  patch.object(callback.webbrowser, "open") as browser):
                if isinstance(result, Exception):
                    browser.side_effect = result
                else:
                    browser.return_value = result
                callback.show_authorization_url("https://identity.test/auth")
                self.assertEqual("https://identity.test/auth" in str(output.call_args_list), result is not True)

    def test_invalid_state_duplicates_and_oversized_body_do_not_consume_flow(self):
        def exercise(address, future):
            for body in ("state=other&code=wrong", "state=expected-state&code=a&code=b", "x=" + "x" * 16384):
                self.assertEqual(self.post(address, body), 400)
                self.assertFalse(future.done())
            body = urlencode({"state": "expected-state", "code": "synthetic-code"})
            self.assertEqual(self.post(address, body), 200)
            self.assertEqual(future.result(timeout=2), {"state": "expected-state", "code": "synthetic-code"})
        self.run_callback(exercise)

    def test_browser_preconnection_does_not_extend_deadline(self):
        now = [0.0]
        clock = SimpleNamespace(monotonic=lambda: now[0])
        def exercise(address, future):
            now[0] = 4.0
            with self.assertRaisesRegex(RuntimeError, "cancelled or timed out"):
                future.result(timeout=2)
        self.run_callback(exercise, clock=clock)

    def test_provider_denial_is_delivered_to_msal(self):
        def exercise(address, future):
            self.assertEqual(self.post(address, "state=expected-state&error=access_denied"), 400)
            self.assertEqual(future.result(timeout=2)["error"], "access_denied")
        self.run_callback(exercise)
