"""The application's origin-scoped TLS adapter; no verifier dependency."""
import httpx
from _confai_transport import Session

class AppraisedTransport(httpx.BaseTransport):
    def __init__(self, session):
        self.session = session

    def handle_request(self, request):
        status, headers, body = self.session.request(request.method, str(request.url), list(request.headers.multi_items()), request.read())
        return httpx.Response(status, headers=headers, content=body, request=request)
