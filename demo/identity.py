"""Interactive email-OTP sign-in for the public desktop client."""

import base64
import secrets
import threading
import time
import webbrowser
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

CLIENT_ID = "71216264-127c-46b3-8772-3bd72cb8e499"
SCOPE = "openid profile email api://f569371d-d5a3-4acc-addd-03f6f383701f/access_as_user"
DISCOVERY = (
    "https://teraveri.ciamlogin.com/"
    "e6c6fd7f-49f0-423d-a06f-d0f89a790372/v2.0/.well-known/"
    "openid-configuration?appid=" + CLIENT_ID
)
REDIRECT = "http://localhost:8765"


def _challenge(verifier):
    digest = sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def sign_in():
    """Return an API access token in memory; never persist it or print OAuth errors."""
    metadata = httpx.get(DISCOVERY, timeout=10.0)
    metadata.raise_for_status()
    endpoints = metadata.json()
    for key in ("authorization_endpoint", "token_endpoint"):
        if not endpoints[key].startswith("https://teraveri.ciamlogin.com/"):
            raise RuntimeError("Unexpected identity endpoint")

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    answer = {}
    received = threading.Event()

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if parsed.path == "/" and params.get("state") == [state]:
                answer["code"] = params.get("code", [None])[0]
                received.set()
                status = 200 if answer["code"] else 400
            else:
                status = 400
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b"Return to the console." if status == 200 else b"Sign-in failed.")

        def log_message(self, *_args):
            pass

    try:
        server = HTTPServer(("127.0.0.1", 8765), Callback)
    except OSError as exc:
        raise RuntimeError("Local sign-in port 8765 is unavailable") from exc
    server.timeout = 1
    query = urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT,
        "response_mode": "query",
        "scope": SCOPE,
        "state": state,
        "code_challenge": _challenge(verifier),
        "code_challenge_method": "S256",
    })
    try:
        if not webbrowser.open(endpoints["authorization_endpoint"] + "?" + query):
            raise RuntimeError("Could not open a browser for sign-in")
        print("Complete email sign-in in your browser.")
        deadline = time.monotonic() + 180
        while not received.is_set() and time.monotonic() < deadline:
            server.handle_request()
        if not answer.get("code"):
            raise RuntimeError("Email sign-in was cancelled or timed out")
    finally:
        server.server_close()

    response = httpx.post(endpoints["token_endpoint"], data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "code": answer["code"],
        "code_verifier": verifier,
        "scope": SCOPE,
    }, timeout=10.0)
    if response.status_code != 200:
        raise RuntimeError("Email sign-in failed")
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Identity provider returned no API access token")
    return token
