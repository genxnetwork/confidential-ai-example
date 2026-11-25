"""Limit admitted chat credentials to the example's API routes."""

import httpx

class ChatTransport(httpx.BaseTransport):
    """Apply application route and token policy before the Confido transport."""

    def __init__(self, peer_transport: httpx.BaseTransport, access_token: str):
        self.peer_transport = peer_transport
        self.access_token = access_token

    def handle_request(self, request):
        if request.url.path not in ("/v1/models", "/v1/chat/completions"):
            raise ValueError("Application request path is not allowed")
        if request.headers.get("authorization") != f"Bearer {self.access_token}":
            raise ValueError("Unexpected application authorization header")
        return self.peer_transport.handle_request(request)

    def close(self):
        self.peer_transport.close()
