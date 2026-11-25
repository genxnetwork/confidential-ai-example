"""Drive the real Docker callback receiver using local HTTP connections."""

import socket
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import patch

from demo import identity_callback as callback


class CallbackTests(unittest.TestCase):
    def run_callback(self, exercise, *, clock=None):
        ready = threading.Event()
        accepted = threading.Event()
        context = {}
        original_server = callback.ThreadingHTTPServer

        class EphemeralServer(original_server):
            def __init__(self, address, handler):
                super().__init__(("127.0.0.1", 0), handler)
                context["address"] = self.server_address

            def get_request(self):
                result = super().get_request()
                accepted.set()
                return result

        def show_url(_url):
            ready.set()

        with (patch.object(callback, "ThreadingHTTPServer", EphemeralServer),
              patch.object(callback, "show_authorization_url", side_effect=show_url),
              patch.object(callback, "time", clock or time),
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
