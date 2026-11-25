"""Automated packaged-image acceptance using real MSAL and synthetic CIAM HTTP.

Each phase runs in a fresh container with the same disposable Docker state volume.
The sign-in phase uses the real callback receiver through a published host port.
No live accounts or credentials are used, and no token is printed.
"""

import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import msal
from demo import identity
from identity_provider import IdentityProvider


def run(phase):
    provider = IdentityProvider()
    def show_url(url):
        response = provider.capture_authorization(url)
        print("CALLBACK_READY " + json.dumps(response), flush=True)
    def no_browser(*args):
        raise AssertionError("Recovery must not start interactive sign-in")
    with ExitStack() as stack:
        stack.enter_context(patch("requests.Session.get", side_effect=provider.get))
        stack.enter_context(patch("requests.Session.post", side_effect=provider.post))
        stack.enter_context(patch("builtins.input", return_value="y"))
        if phase == "signin":
            provider.lifetime = -3600
            stack.enter_context(patch("demo.identity_callback.show_authorization_url", side_effect=show_url))
            session = identity.authenticate()
            assert session.access_token == "synthetic-access-1"
            assert provider.posts[0]["grant_type"] == "authorization_code"
            assert identity.cache_path().stat().st_mode & 0o777 == 0o600
            print("SIGN_IN_OK MSAL=" + msal.__version__)
            return
        stack.enter_context(patch.object(identity, "receive_response", side_effect=no_browser))
        if phase == "outage":
            before = identity.cache_path().read_bytes()
            provider.failure = (503, {"error": "temporarily_unavailable"})
            try:
                identity.authenticate()
            except identity.SessionUnavailable:
                pass
            else:
                raise AssertionError("Expected temporary failure")
            assert identity.cache_path().read_bytes() == before
            print("OUTAGE_PRESERVED_CACHE")
        elif phase in ("recover", "cached", "logoff"):
            session = identity.authenticate()
            assert session.token() == "synthetic-access-1"
            if phase == "recover":
                assert len(provider.posts) == 1
                assert provider.posts[0]["grant_type"] == "refresh_token"
                assert provider.posts[0]["refresh_token"] == "synthetic-refresh-1"
                print("RESTART_SILENT_RENEWAL_OK")
            else:
                assert not provider.posts
                print("RESTART_CACHE_HIT_OK")
            if phase == "logoff":
                identity.logoff(session)
                assert not identity.create_application().get_accounts()
                print("LOCAL_LOGOFF_OK")
        else:
            raise ValueError("Unknown acceptance phase")


if __name__ == "__main__":
    run(sys.argv[1])
