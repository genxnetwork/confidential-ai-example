# Browser acceptance and identity boundaries

The browser-runner migration described below is merged into JAN Confido `main`
through [PR #8](https://github.com/jandigitrust/confido/pull/8); identity code was
unchanged by the browser migration. Enrollment
has separately moved to `/mnt/sanctio`, an unpublished project without Git.

## Browser checks

Before migration, `tools/browser_live_checks.py` loaded a packaged Chromium
extension, located its service worker and verifier page, supplied a policy,
invoked live collection, and checked match/mismatch evidence-only results.
That acceptance flow neither opens chat nor tests
the Python client's pinned HTTPS transport. Its main subject is Confido's browser
integration, not the OpenAI-compatible example.

Confido already has `scripts/browser_checks.py` for worker/Python/CLI parity,
collection contracts, installed-extension replay, mixed assets, and CSP. The
live runner adds real deployment delivery to those offline checks.
Keep live acceptance separate from deterministic checks: external DNS, browser
TLS, AMD KDS, GitHub, and the deployed VM can fail independently of a code change.

The original script had two important evidence limits:

- It changed optional permissions into granted host permissions in a temporary
  copy. This exercises a preauthorized package, not the production permission
  request, denial, or revocation flow.
- It selected `verifier-match.json` and `verifier-mismatch.json`, the legacy Milan
  pair. The Docker application selects Genoa policies. Neither the current
  deployment's hardware nor acceptance against those alternative pins was
  established during this inspection. The new case file selects Genoa explicitly.

The owner is now Confido's extension integration suite. Its live runner accepts
deployment cases as local inputs: an approved origin, policy path, and expected
evidence status/reason. It resolves policy paths relative
to the case file, not a sibling checkout assumed by the harness. GENXT-specific
origins, policy approval, and deployment acceptance remain application/operator
fixtures. The runner must not discover trust policy from the evidence endpoint.

Keep packaged-extension setup, selectors, worker startup, timeouts, assertions,
and cleanup with Confido. Reuse small setup helpers only where both existing
harnesses have the same lifecycle. Do not make a new generic browser framework
or force the live-only check to install every Python/CLI parity dependency.

Retain distinct checks for denied/granted permissions, local verification of
valid/invalid evidence, and opt-in live delivery. Pregranting can remain a clearly
labeled test mode, but is not evidence that the actual consent UI works.
The new runner exposes pregranting explicitly and supports headed Chromium for
operator-driven consent. Native consent-flow acceptance remains separate from
the deterministic API-stub checks; consult Confido’s dated acceptance records
for the browser and deployment actually exercised.
Keep the application's own no-token-before-admission and chat tests here.

## OAuth and session handling

The demo now uses MSAL Python directly for the existing Entra CIAM public client.
All integration is application-owned under `demo/`; the experimental Aditus
extraction has been superseded and is no longer imported or required for builds.

| Responsibility | Owner |
| --- | --- |
| Authorization Code/PKCE, code exchange, token renewal and account cache semantics | MSAL Python |
| Cache serialization | MSAL Python |
| File persistence interface and cross-process locking | MSAL Extensions |
| Reload/commit boundary for successful operations | Demo integration |
| Private atomic cache writes and state-volume choice | Demo deployment integration |
| Authority, client ID, API scopes and registered callback | Application/identity deployment |
| Callback HTTP delivery into Docker | `demo/identity_callback.py` |
| Identity display, saved-account selection, continue/logoff prompts | Application UX |
| Permitted token destinations and application admission | Application plus Confido's separately scoped HTTPS transport |

MSAL's two auth-code APIs allow the application to deliver the host browser's
callback into Docker without reimplementing PKCE, token exchange or JWT decoding.
The receiver accepts bounded form POSTs and forwards the response to MSAL for
protocol validation. The API scope stays explicit; MSAL supplies its reserved
OIDC scopes. The CIAM authority is pinned and global instance discovery disabled.

This minimal Linux container explicitly uses private plaintext persistence,
without assuming a desktop keychain or silently falling back from encryption.
The MSAL cache is partitioned by client, authority and scopes. A storage error
fails the operation with a safe diagnostic; atomic replacement preserves the
previous cache when a write fails. This replaces the legacy memory-only warning
on persistence failure. Temporary provider/network failures and incomplete
responses preserve saved authorization and do not trigger automatic login.

Legacy raw-token session files are not migrated into MSAL. A successful fresh
sign-in removes the obsolete file. Declining or failing that sign-in preserves
it. The user procedure is in the root README.

Automated tests exercise the real MSAL library through a synthetic CIAM HTTP
boundary. Packaged-image checks additionally exercise host-port callback delivery
and session recovery across fresh containers using the same disposable volume.
These tests do not establish live CIAM sign-in or app-registration compatibility;
that acceptance requires an operator to complete browser authentication.

## Decision: defer Aditus extraction

Status: accepted for this demo; supersedes the local experimental extraction.
The first consumer did not establish a reusable contract. Maintaining a custom
OAuth implementation in a separate repository added distribution work before
showing value beyond existing identity libraries.

Keep the integration in this application and delegate protocol mechanics to MSAL.
After one or two further consumers work with their own OAuth libraries, compare
actual requirements for configuration, cache partitioning, account selection and
stable errors. Extract into Aditus only if that comparison identifies meaningful
shared behavior. Rust remains an open implementation choice for a demonstrated
shared need, rather than a reason to create that need.

The acceptance scenario is: a temporary renewal outage after a successful login
must preserve the persisted cache byte-for-byte, send no Flint request, and allow
silent recovery after service restoration and container restart. The enforcement
points are MSAL result classification, the persisted cache and application request
gating; unit and image-boundary tests cover those points. The tradeoff is a small
application adapter today while reuse remains unproven.

References: [MSAL acquisition](https://learn.microsoft.com/en-us/entra/msal/python/getting-started/acquiring-tokens),
[MSAL Extensions](https://github.com/AzureAD/microsoft-authentication-extensions-for-python).
