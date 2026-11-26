# Attestation and admission flow

Chat uses a preconfigured OpenAI-compatible service after evidence and HTTPS
peer checks. The [root README](../README.md) describes launch and chat behavior.
Replies are buffered and capped at 256 generated tokens within the Confido
transport's 30-second request budget. Inference runs
outside the appraised VM and is outside its attestation coverage.

The [policy catalog](../profiles/README.md) identifies the enrolled references,
their stage status, and the deliberately mismatched fixture.

At startup, before endpoint selection, the console signs in once through Teraveri
Identity using MSAL Python's Authorization Code flow with PKCE. A saved session shows the identity
and asks `Continue? [Y/logoff]`. `logoff` deletes the saved local session and offers
a new sign-in with account selection; it does not sign out other browser apps.
Access and refresh tokens stay in a private `0600` file in the state volume,
under `/state/confidential-ai-example/msal-<deployment-hash>.json`. MSAL supplies cache serialization and MSAL Extensions supplies file locking.
The application reloads under the lock and commits successful acquisitions with
atomic private file replacement.
The cache is unencrypted at rest, with no desktop keychain dependency.
Tokens are refreshed silently
when possible. The same sign-in is reused when switching endpoints and restarting
or updating the container. Archives live under `/state/confidential-ai-example/runs/`.
Temporary identity-service or network failures keep the saved session. A confirmed
OAuth rejection offers a new sign-in. Empty or incomplete acquisition results
preserve the cache and withhold the request. A legacy `session.json` file cannot
restore a session; successful interactive sign-in removes it. Declining or
failing sign-in preserves that file.
The application receives a bounded authorization-code query redirect and passes
it to MSAL for state, nonce and PKCE handling. Code exchange stays on HTTPS;
the local HTML page removes the query from browser history and sends no referrer.
Legacy form POST callbacks remain accepted for already-open sign-in pages.
Sign-in allows 180 seconds for the browser
callback; an incomplete browser connection does not block that deadline.

The query response is an intentional native-client choice: an HTTPS form POST
to the HTTP loopback receiver can prompt Safari for confirmation. Only a one-use
code traverses the loopback URL, guarded by PKCE and state. The callback serves no external
resources, sets `Referrer-Policy: no-referrer` and clears the URL query. See
[MSAL's response-mode contract](https://msal-python.readthedocs.io/en/stable/#msal.ClientApplication.initiate_auth_code_flow).

The Docker launchers open the browser on the host. A per-launch local handoff
path becomes available only after the callback listener has started, then
redirects the browser to MSAL's authorization URL. Each interactive flow has its
own readiness marker so later reauthentication can open the browser again.
The console shows the full authorization URL only if this navigation has not
occurred within five seconds, or when automatic opening is unavailable/disabled.
The handoff path never accepts OAuth codes: the actual response must reach the
bounded, state-matching root callback. The listener uses `GENXT_DEMO_CALLBACK_BIND`
(`0.0.0.0` inside the image, loopback by default natively).

Fatal startup errors return a nonzero exit status. Request errors show a safe
classification or HTTP status without printing server error bodies or tokens.

`POST /tee-report` requires no application login.
After evidence and TLS-peer checks, the scoped transport sends the user's access
token only to the appraised `/v1/models` and `/v1/chat/completions` routes. The service validates the
user's access token. Host port 8765 must be available. Docker maps only
`127.0.0.1:8765` to the callback listener inside the container.
The isolated acceptance uses a synthetic downstream.
Decline, sign-in failure, collection failure, mismatched evidence and peer failure
withhold the chat request. A mismatch sends no user access token to the demo VM.
Bootstrap retrieval is unauthenticated; an explicit application-policy option
permits self-signed bootstrap. Confido's client checks the attested certificate's
exact DER, hostname and validity on every connection; other origins and
redirects are rejected. Its transport is reusable across applications, while
this example owns the email sign-in, API route limits and admission decision.

The [profile catalog](../profiles/README.md) and [application schemas](../schemas/README.md)
explain each demo policy and application decision. Genoa is the AMD EPYC
processor generation of the local test VM; the original Milan demo uses a
different generation and enrollment.
Application profiles contain a locally approved HTTPS origin and a
`verifier_policy` filename.
Verifier policies contain the independently enrolled root, platform and reference.
Match/mismatch use the same verifier code path with different local reference pins.
This repository owns these demo policies. The Genoa stage enrollment inputs and
positive/negative policies live under `profiles/`. The positive policy was
generated after checking the GENXT publisher statement at enrollment.
The positive reference is a stage candidate in the
[Teraveri registry](https://github.com/teraveri/reference-value-registry); the
negative reference is an unendorsed fixture there, not an alternative trusted
baseline. During each run the Confido client downloads the exact `reference.json`
at the policy's full Git commit and checks its SHA-256 and measurements.
The publisher statement is checked at enrollment, not rechecked on each run.
Neither a registry update nor a new branch tip changes an existing pin. If the
pinned file cannot be retrieved, the application withholds chat.
The browser extension's approved demo origins are in
[`profiles/extension-origins.json`](../profiles/extension-origins.json).
The generic verifier accepts policy bytes supplied by its caller and does not
choose these trust pins.
The Confido client sends a nonce directly to `POST /tee-report`; no metadata discovery
selects the report endpoint or a reference. After evidence appraisal, an
unauthenticated `HEAD /tee-report` over quote-bound certificate-pinned TLS
authenticates the intended peer before the application sends a request.
The run directory holds a v2 verification archive, `.runtime.json` with build
metadata and appraisal timing, and a separate `.decision.json`;
only the latter contains `application_admitted`.

The quote binds nonce, certificate and IMA log. There is no TLS session binder or
relay-resistance claim. Coverage is enrolled boot aggregate/kernel modules;
application/model/GPU state are outside that coverage. The VM's attestation
does not attest the external model, runtime or inference output.
The browser extension in the Confido repository performs evidence checks entirely
in WASM and does not use this transport or send chat prompts.

## Runtime and attestation output

Detailed attestation output comes from `confido_client.console`; the application
calls `print_verification(attempt)` and prints its own admission decision.
At startup, the example checks Python 3.15, verifier pipeline revision 2 and the
public client APIs it uses. Incompatibility produces image update instructions;
startup does not invoke pip, download a wheel, hash application sources or require
build artifacts. Each run records the installed client's build metadata separately
from its application decision. `./run --info` can also show the optional installation
record; deleting that record does not disable a compatible installed client.

Caller collection events have real UTC timestamps; completed verifier stages are
printed in their returned order without invented per-stage timestamps. All IMA
entries appear immediately before the IMA comparison verdict, with full file
hashes and per-entry `MATCH` or `MISMATCH` labels when the pinned reference has
been checked. An early failure still shows the received entries as `UNVERIFIED`.
The archive retains full values. Successful labels use ANSI green 32; reference
links are blue. `CONFIDO_COLOR=always|auto|never` controls terminal color.

The final summary separates evidence verification from application admission.
The 120-second monotonic challenge deadline is checked again after rendering and
the pinned TLS peer check. A live run is one-use; loading an old archive cannot
restore it. An expired run or a failed TLS peer never opens chat.

## Reviewer checks

Use the launch and local-build commands in the [root README](../README.md),
with a dedicated state volume when testing sign-in and logoff.

1. Select match, allow collection and require verified evidence and an
   authenticated HTTPS peer before the application sends a chat request.
2. Select mismatch and require denial with no chat request or user token sent.
3. Decline collection and require that chat remains closed.
4. Restart with the same state volume and check saved-session reuse. Exercise
   local logoff and a fresh browser sign-in separately.
5. Read the policy catalog and measurement limits above. A successful chat
   demonstrates application admission; it does not attest inference.

The automated suite uses controlled identity, evidence and peer collaborators
for these boundaries. A local test pass does not establish live browser sign-in,
public deployment state or registry publication.
