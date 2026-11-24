"""The application's origin-scoped TLS adapter; no verifier dependency."""

import httpx

SDK_PLACEHOLDER_API_KEY = "not-a-credential"


class AppraisedTransport(httpx.BaseTransport):
    """Send only to the appraised origin, without SDK placeholder authentication."""

    def __init__(self, session):
        self.session = session

    def handle_request(self, request):
        request_headers = []
        for name, value in request.headers.multi_items():
            if name.lower() == "authorization":
                if value != f"Bearer {SDK_PLACEHOLDER_API_KEY}":
                    raise ValueError("This demo does not accept application credentials")
                continue
            request_headers.append((name, value))
        status, response_headers, body = self.session.request(
            request.method,
            str(request.url),
            request_headers,
            request.read(),
        )
        return httpx.Response(status, headers=response_headers, content=body, request=request)
