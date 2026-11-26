"""Synthetic CIAM HTTP boundary for exercising the real MSAL implementation.

No MSAL acquisition or cache method is replaced. Tokens and identities in this
fixture are synthetic and have no access to a live service.
"""

import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlsplit

import requests

from demo import identity


def encode_json(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()


class IdentityProvider:
    """Provide discovery and token responses while recording requests for assertions."""

    def __init__(self):
        self.posts = []
        self.gets = []
        self.query = None
        self.failure = None
        self.lifetime = 3600
        self.token_number = 0
        self.nonce_override = None
        self.omit_id_token = False

    def get(self, url, **kwargs):
        self.gets.append(url)
        if url.startswith(identity.AUTHORITY) and ".well-known/openid-configuration" in url:
            return self.response(200, {
                "authorization_endpoint": identity.AUTHORITY + "/oauth2/v2.0/authorize",
                "token_endpoint": identity.AUTHORITY + "/oauth2/v2.0/token",
                "issuer": identity.AUTHORITY + "/v2.0",
            })
        raise AssertionError("Unexpected discovery destination")

    def capture_authorization(self, url):
        self.query = parse_qs(urlsplit(url).query)
        return {"state": self.query["state"][0], "code": "synthetic-code"}

    def post(self, url, data=None, **kwargs):
        assert url == identity.AUTHORITY + "/oauth2/v2.0/token"
        self.posts.append(dict(data))
        if self.failure is not None:
            if isinstance(self.failure, Exception):
                raise self.failure
            return self.response(*self.failure)
        self.token_number += 1
        result = {
            "access_token": f"synthetic-access-{self.token_number}",
            "refresh_token": f"synthetic-refresh-{self.token_number}",
            "expires_in": self.lifetime,
            "scope": " ".join(identity.SCOPES), "token_type": "Bearer",
            "client_info": encode_json({"uid": "synthetic-user", "utid": "synthetic-tenant"}),
        }
        if data["grant_type"] == "authorization_code":
            verifier = data["code_verifier"]
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            assert challenge == self.query["code_challenge"][0]
            assert self.query["code_challenge_method"] == ["S256"]
            assert data["redirect_uri"] == identity.REDIRECT
            if self.omit_id_token:
                return self.response(200, result)
            claims = {
                "aud": identity.CLIENT_ID, "iss": identity.AUTHORITY + "/v2.0",
                "oid": "synthetic-user", "sub": "synthetic-user", "tid": "synthetic-tenant",
                "preferred_username": "user@example.test", "iat": int(time.time()),
                "exp": int(time.time()) + 3600, "nonce": self.nonce_override or self.query["nonce"][0],
            }
            result["id_token"] = encode_json({"alg": "none"}) + "." + encode_json(claims) + "."
        return self.response(200, result)

    @staticmethod
    def response(status, payload):
        result = requests.Response()
        result.status_code = status
        result._content = json.dumps(payload).encode()
        result.headers["Content-Type"] = "application/json"
        return result
