"""Bounded loopback HTTP delivery for MSAL's Docker browser callback.

The receiver transports the response to MSAL, which owns OAuth state, nonce and
PKCE validation. No token request or token decoding happens here.
"""

import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SIGN_IN_TIMEOUT = 180
CALLBACK_PORT = 8765


def show_authorization_url(url):
    """Open the browser or show the link for the Docker host's browser."""
    if webbrowser.open(url):
        print("Complete email sign-in in your browser.")
    else:
        print("Open this sign-in URL in a browser on this machine: " + url)


def receive_response(url, state):
    """Receive one state-matching response before the monotonic sign-in deadline.

    Request handlers have idle timeouts and run independently, so an incomplete
    browser connection cannot block another callback or extend the login window.
    """
    answer = {}
    received = threading.Event()
    answer_lock = threading.Lock()
    deadline = time.monotonic() + SIGN_IN_TIMEOUT

    class Callback(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(1.0)

        def do_POST(self):
            """Accept only a bounded form response; MSAL validates its OAuth meaning."""
            status = 400
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if (not 0 < length <= 16384 or self.headers.get("Transfer-Encoding")
                        or self.headers.get_content_type() != "application/x-www-form-urlencoded"):
                    raise ValueError("Unsupported callback body")
                body = self.rfile.read(length).decode("utf-8")
                params = parse_qs(body, keep_blank_values=True, max_num_fields=16)
                with answer_lock:
                    # Reject mismatches without consuming the active login. The
                    # first valid response wins even with concurrent requests.
                    if (urlparse(self.path).path == "/"
                            and params.get("state") == [state]
                            and all(len(values) == 1 for values in params.values())
                            and not received.is_set()
                            and time.monotonic() < deadline):
                        answer.update({key: values[0] for key, values in params.items()})
                        received.set()
                        status = 200 if answer.get("code") else 400
            except (ValueError, UnicodeError, OSError):
                pass
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b"Return to the console." if status == 200 else b"Sign-in failed.")

        def do_GET(self):
            """Do not accept codes in URLs; this application requests form_post."""
            self.send_error(400, "A form callback is required")

        def log_message(self, *_args):
            pass

    bind = os.environ.get("CONFIDO_AUTH_CALLBACK_BIND", "127.0.0.1")
    if bind not in ("127.0.0.1", "0.0.0.0"):
        raise RuntimeError("Unsupported sign-in callback bind address")
    try:
        # A browser preconnection must not block the callback or its deadline.
        server = ThreadingHTTPServer((bind, CALLBACK_PORT), Callback)
    except OSError as exc:
        raise RuntimeError("Local sign-in port 8765 is unavailable") from exc
    server.timeout = 1
    try:
        show_authorization_url(url)
        while not received.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            server.timeout = min(1.0, remaining)
            server.handle_request()
        if not received.is_set():
            raise RuntimeError("Email sign-in was cancelled or timed out")
    finally:
        server.server_close()
    return answer
