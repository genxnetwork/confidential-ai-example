"""The application's origin-scoped TLS adapter; no verifier dependency."""

import httpx

SDK_PLACEHOLDER_API_KEY = "not-a-credential"


class AppraisedTransport(httpx.BaseTransport):
    """Replace the SDK placeholder with a user token for admitted API routes."""

    def __init__(self, session, access_token):
        self.session = session
        self.access_token = access_token

    def handle_request(self, request):
        if request.url.path not in ("/v1/models", "/v1/chat/completions"):
            raise ValueError("Application request path is not allowed")
        request_headers = []
        for name, value in request.headers.multi_items():
            if name.lower() == "authorization":
                if value != f"Bearer {SDK_PLACEHOLDER_API_KEY}":
                    raise ValueError("Unexpected application authorization header")
                continue
            request_headers.append((name, value))
        request_headers.append(("authorization", "Bearer " + self.access_token))
        status, response_headers, body = self.session.request(
            request.method,
            str(request.url),
            request_headers,
            request.read(),
        )
        return httpx.Response(status, headers=response_headers, content=body, request=request)
