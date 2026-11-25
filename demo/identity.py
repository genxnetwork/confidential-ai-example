"""Application-owned MSAL integration for Entra CIAM and the console sign-in UX.

MSAL owns PKCE, token exchange, accounts and renewal. MSAL Extensions supplies
persistence and locking; acquisitions commit cache changes only on success. This Linux-container deployment explicitly uses a private,
unencrypted cache in its state volume; no desktop keychain is assumed.
"""

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import msal
import requests
from msal.exceptions import MsalError
from msal_extensions import CrossPlatLock, FilePersistence
from msal_extensions.persistence import PersistenceNotFound

from demo.identity_callback import receive_response

CLIENT_ID = "71216264-127c-46b3-8772-3bd72cb8e499"
AUTHORITY = "https://teraveri.ciamlogin.com/e6c6fd7f-49f0-423d-a06f-d0f89a790372"
# MSAL adds its reserved openid/profile/offline_access scopes itself.
SCOPES = ["email", "api://f569371d-d5a3-4acc-addd-03f6f383701f/access_as_user"]
REDIRECT = "http://localhost:8765"


class AuthenticationRequired(RuntimeError):
    """The cache cannot satisfy the request without a new interactive sign-in."""


class SessionUnavailable(RuntimeError):
    """Identity or local storage failed; saved authorization must be preserved."""


def state_directory():
    """Locate this application's state, including the mounted Docker volume."""
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "confidential-ai-example"


def cache_path():
    """Partition the cache by the deployment's client, authority and API scopes."""
    partition = sha256("\n".join([CLIENT_ID, AUTHORITY, *SCOPES]).encode()).hexdigest()[:20]
    return state_directory() / f"msal-{partition}.json"


class PrivateFilePersistence(FilePersistence):
    """Keep MSAL Extensions' file interface with private, atomic POSIX writes.

    Atomic replacement preserves the previous cache if writing fails and keeps
    readers from observing a partial JSON document. Extensions supplies locking.
    """

    def save(self, content):
        path = Path(self.get_location())
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             delete=False) as stream:
                temporary = Path(stream.name)
                os.fchmod(stream.fileno(), 0o600)
                stream.write(content)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


@contextmanager
def cached_operation(app):
    """Reload and commit one successful MSAL operation under the Extensions lock.

    MSAL may evict expired access tokens before a refresh fails. Keep those
    mutations in memory until success so an outage cannot alter saved state.
    Hold the same lock through refresh/commit and account removal to prevent an
    older acquisition from restoring credentials after another process logs off.
    Browser interaction happens outside this lock.
    """
    path = cache_path()
    persistence = PrivateFilePersistence(str(path))
    try:
        with CrossPlatLock(str(path) + ".lockfile"):
            try:
                original = persistence.load()
            except PersistenceNotFound:
                original = ""
            app.token_cache.deserialize(original)
            try:
                yield
                if app.token_cache.has_state_changed:
                    persistence.save(app.token_cache.serialize())
            except BaseException:
                # Preserve both the on-disk snapshot and this client's in-memory
                # credentials if acquisition, cancellation or persistence fails.
                app.token_cache.deserialize(original)
                raise
    except (AuthenticationRequired, SessionUnavailable):
        raise
    except RuntimeError as error:
        raise SessionUnavailable("Sign-in or cache operation could not be completed") from error


def create_application():
    """Create the CIAM public client; never initialize networking during import."""
    try:
        path = cache_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.parent.chmod(0o700)
        if path.exists() and path.stat().st_mode & 0o077:
            raise SessionUnavailable("Saved sign-in cache permissions are not private")
        cache = msal.SerializableTokenCache()
        app = msal.PublicClientApplication(
            CLIENT_ID, authority=AUTHORITY, token_cache=cache,
            # This application pins its CIAM authority. Discovery stays on that
            # authority; no global instance-discovery/alias service is needed.
            instance_discovery=False, timeout=10, enable_pii_log=False,
        )
        with cached_operation(app):
            pass
        return app
    except (OSError, ValueError, KeyError, TypeError, AttributeError, MsalError, requests.RequestException) as error:
        raise SessionUnavailable("Sign-in service or saved cache is unavailable") from error


def display_identity(account):
    """Use account metadata only as an escaped display label, never for admission."""
    label = account.get("username") or account.get("name") or "Teraveri user"
    return "".join(c for c in str(label) if c.isprintable())[:200]


def require_token(result):
    """Classify MSAL results without exposing remote bodies or nested diagnostics."""
    if isinstance(result, dict) and isinstance(result.get("access_token"), str) and result["access_token"]:
        return result["access_token"]
    # An empty silent result can also follow an incomplete provider response.
    # It does not establish revocation, so preserve the saved account/cache.
    if isinstance(result, dict) and result.get("error") in (
        "invalid_grant", "interaction_required", "login_required", "consent_required",
    ):
        raise AuthenticationRequired("Please sign in again")
    raise SessionUnavailable("Session could not be renewed")


@dataclass
class Session:
    """Bind API token acquisition to one MSAL account without exposing credentials."""

    app: object = field(repr=False)
    account: dict = field(repr=False)
    access_token: str = field(default="", repr=False)

    @property
    def identity(self):
        return display_identity(self.account)

    def token(self):
        """Let MSAL use its cache or renew; preserve credentials on transient failure."""
        try:
            with cached_operation(self.app):
                result = self.app.acquire_token_silent_with_error(SCOPES, account=self.account)
                token = require_token(result)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, MsalError, requests.RequestException) as error:
            raise SessionUnavailable("Session could not be renewed") from error
        self.access_token = token
        return token


def choose_account(accounts):
    """Require an explicit selection when the application's cache has several users."""
    if len(accounts) == 1:
        return accounts[0]
    for index, account in enumerate(accounts, 1):
        print(f"{index}. {display_identity(account)}")
    while True:
        answer = input("Choose saved account number, or logoff: ").strip().lower()
        if answer in ("logoff", "logout"):
            return None
        if answer.isdecimal() and 1 <= int(answer) <= len(accounts):
            return accounts[int(answer) - 1]
        print("Choose a listed account number or logoff.")


def logoff(session):
    """Remove the selected account from this application's MSAL cache only."""
    try:
        with cached_operation(session.app):
            session.app.remove_account(session.account)
        (state_directory() / "session.json").unlink(missing_ok=True)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SessionUnavailable("Local sign-out could not be saved") from error


def sign_in(app):
    """Use MSAL's auth-code APIs with the application's Docker callback receiver."""
    try:
        flow = app.initiate_auth_code_flow(
            SCOPES, redirect_uri=REDIRECT, prompt="select_account", response_mode="query",
        )
        response = receive_response(flow["auth_uri"], flow["state"])
        with cached_operation(app):
            result = app.acquire_token_by_auth_code_flow(flow, response)
            token = require_token(result)
            accounts = app.get_accounts()
            claims = result.get("id_token_claims", {})
            account_id = claims.get("oid") or claims.get("sub")
            matches = [a for a in accounts
                       if account_id and a.get("local_account_id") == account_id]
            if len(matches) != 1:
                raise SessionUnavailable("The signed-in account could not be selected")
            account = matches[0]
            # Legacy raw-token files are not imported. A successful MSAL sign-in
            # replaces their purpose, so remove this app's obsolete credentials.
            (state_directory() / "session.json").unlink(missing_ok=True)
            return Session(app, account, token)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError, MsalError, requests.RequestException) as error:
        if isinstance(error, (SessionUnavailable, AuthenticationRequired)):
            raise
        raise SessionUnavailable("Browser sign-in could not be completed") from error


def authenticate():
    """Offer saved accounts or explicit login; transient failure never logs off."""
    app = create_application()
    try:
        accounts = app.get_accounts()
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SessionUnavailable("Saved sign-in cache is unavailable") from error
    if accounts:
        account = choose_account(accounts)
        if account is None:
            for candidate in accounts:
                logoff(Session(app, candidate))
        else:
            session = Session(app, account)
            print(f"Signed in as {session.identity}.")
            while True:
                answer = input("Continue? [Y/logoff]: ").strip().lower()
                if answer in ("", "y", "yes", "да"):
                    try:
                        session.token()
                        return session
                    except AuthenticationRequired:
                        print("Saved session expired or was revoked. Please sign in again.")
                        logoff(session)
                        break
                if answer in ("logoff", "logout"):
                    logoff(session)
                    print("Signed out locally.")
                    break
                print("Choose yes or logoff.")
    elif (state_directory() / "session.json").exists():
        print("Sign-in storage has changed to MSAL. Please sign in once again.")
    if input("Sign in to continue? [Y/n]: ").strip().lower() not in ("", "y", "yes", "да"):
        return None
    session = sign_in(app)
    print(f"Signed in as {session.identity}.")
    return session
