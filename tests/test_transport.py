"""Real loopback TLS reconnects; synthetic certificates, no hardware claim."""

import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from _confai_transport import Session


class TransportTests(unittest.TestCase):
    def test_reconnect_rejects_rotated_leaf_before_application_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            certs = []
            for name in ("a", "b"):
                cert = root / (name + ".pem")
                key = root / (name + ".key")
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:2048",
                        "-nodes",
                        "-days",
                        "1",
                        "-subj",
                        "/CN=localhost",
                        "-addext",
                        "subjectAltName=DNS:localhost",
                        "-keyout",
                        str(key),
                        "-out",
                        str(cert),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(cert, key)
                certs.append(ctx)
            observed = []

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    observed.append(self.path)
                    self.send_response(302 if self.path == "/redirect" else 200)
                    self.send_header("Content-Length", "0")
                    self.send_header("Connection", "close")
                    if self.path == "/redirect":
                        self.send_header("Location", "https://other.invalid/forbidden")
                    self.end_headers()

                def log_message(self, *args):
                    pass

            class Server(ThreadingHTTPServer):
                context = certs[0]

                def get_request(self):
                    sock, addr = super().get_request()
                    try:
                        return self.context.wrap_socket(sock, server_side=True), addr
                    except Exception:
                        sock.close()
                        raise

                def handle_error(self, *args):
                    pass

            server = Server(("127.0.0.1", 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                origin = f"https://localhost:{server.server_port}"
                der = ssl.PEM_cert_to_DER_cert((root / "a.pem").read_text())
                session = Session(origin, der)
                self.assertEqual(
                    session.request("GET", origin + "/ok", [], b"")[0], 200
                )
                with self.assertRaisesRegex(RuntimeError, "redirect"):
                    session.request("GET", origin + "/redirect", [], b"")
                server.context = certs[1]
                with self.assertRaises(RuntimeError):
                    session.request(
                        "GET",
                        origin + "/secret",
                        [("authorization", "synthetic-sentinel")],
                        b"",
                    )
                self.assertEqual(observed, ["/ok", "/redirect"])
            finally:
                server.shutdown()
                server.server_close()
