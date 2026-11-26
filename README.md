# Confidential AI example

A client-side demonstration of how an application can use attestation before
sending an application request. In isolated tests, the matching case sends one
synthetic request after evidence and TLS-peer checks; the deliberately
mismatched reference causes the application to deny it. This demonstrates the
decision flow, not the integrity of the application, GPU, model, or inference
runtime. See Confido's
[security model](https://github.com/jandigitrust/confido/blob/main/docs/security-model.md)
for the underlying trust chain and terminology.

This is a development and staging example using an alpha SDK. Production use
is unsupported.

A cooperating client separates evidence verification from application admission.
The installed [JAN Confido](https://github.com/jandigitrust/confido) client wheel
retrieves the report and pinned reference, appraises evidence, and authenticates
the HTTPS peer. `demo/admission.py` applies the application's policy before chat;
`demo/transport.py` limits where the user's access token can be sent.
[Attestor](https://github.com/jandigitrust/attestor) provides native evidence
collection and `POST /tee-report` on the demo VM.
The component guides cover [`demo/`](demo/README.md),
[`scripts/`](scripts/README.md), and [`tests/`](tests/README.md).

## Current Genoa demo

Install and start Docker with Linux containers. On macOS and Windows this is
normally Docker Desktop. Python, Rust, make and model weights are not required
on the user's machine.

Linux / macOS:

```sh
./run
```

Windows PowerShell or Command Prompt:

```powershell
.\run.cmd
```

The launcher downloads `ghcr.io/genxnetwork/confidential-ai-example:latest` once
and reuses it on subsequent starts. It starts the Genoa demo, publishes the
sign-in callback only on host loopback port 8765, and persists sign-in and run
archives in the Docker volume `confidential-ai-example-state`. The launcher opens
the host's default browser when sign-in is needed. If the sign-in page is not
reached within five seconds, the console prints the full link for manual opening.
At the next launch, the console shows the saved identity and offers to continue
or log off.

Automatic opening uses `open` on macOS, `xdg-open` on Linux (both with `curl`),
and the default URL handler on Windows. Without an opener, use the printed link.
Set `CONFIDO_BROWSER=manual` to always show the link, for example over SSH or
with a remote Docker host. The browser must reach that host through
`localhost:8765` in either mode.

`./run --setup` downloads the image without signing in; `./run --info` shows its
installed Confido build. `./run --update` explicitly pulls a newer image and
shows its build information. The same options work with `.\run.cmd` on Windows.
Ordinary launches do not rebuild the image or replace the verifier dependency.

This repository's image workflow builds one image, runs the application suite
and packaged session-recovery checks, then publishes that same image to GHCR.
The default branch supplies `latest`; other pushed branches receive their own
image tags and commit tags. The image package must be made public after its
first publication for anonymous pulls. These local changes are not yet published.
The compatible upstream alpha wheel is available; the
[dated readiness record](docs/release-readiness-20261125.md) identifies the
wheel and locally tested image, completed checks and remaining live acceptance.

Inside the image build, the GitHub API selects the latest successful main-branch
`Client wheel` push build from [JAN Confido](https://github.com/jandigitrust/confido).
`nightly.link` provides the download without a GitHub token. The archive SHA-256
must match GitHub metadata before the wheel is loaded. Missing or expired
artifacts stop the build. Installation uses `--no-index --no-deps`, and a small
record captures the exact wheel hash, build information and GitHub run/commit.
A running image needs neither a retained wheel nor that optional record.

There is one image target: `linux/amd64`, including on Windows and Apple Silicon.
Docker Desktop supplies the required Linux environment and architecture
emulation on ARM Macs. Package locks therefore contain one exact wheel hash per
version for CPython 3.15 / Linux x86_64. Enrollment and its cryptography dependencies live in the separate
`../sanctio/` project; neither image stage installs them.

Overrides are optional: `CONFIDO_IMAGE` selects an image/tag,
`CONFIDO_STATE_VOLUME` selects a separate named volume, and `CONFIDO_POLICY_DIR`
binds a host policy directory read-only. The default image uses the checked-in
Genoa stage policies; the application still chooses admission locally. Changing
images or updating does not delete the state volume. Native sessions from earlier
revisions are not automatically imported into that volume.

## Sign-in and admission

The console signs in through Teraveri Identity before endpoint selection.
On later launches it shows the saved identity and offers continue or local
logoff. Tokens stay in a private session file in the Docker state volume;
temporary renewal failures preserve that session.

For each selected endpoint, the application asks Confido to collect and appraise
fresh evidence against its local policy, authenticates the quote-bound HTTPS
peer, then creates an OpenAI client using Confido's transport. Only the admitted
`/v1/models` and `/v1/chat/completions` routes receive the user's access token.
A mismatch or failed peer check withholds chat. Flint serves the
`llama-default` model alias, routed to the `llama-chat-primary` deployment in
Azure AI Foundry. Flint uses a separate Azure resource key stored server-side;
the client sends only its Entra access token to Flint. No model weights run on
the client.

Llama inference runs in Azure, outside the appraised VM. Demo replies are capped
at 256 generated tokens and use a concise-answer prompt. The current Confido
transport has a 30-second request budget. The console shows when generation
starts; responses are buffered, not streamed. Long prompts or slow generation
can still time out. A transport failure does not trigger an automatic inference
retry.

Chat accepts UTF-8 text, including Cyrillic and emoji. Malformed terminal input
is rejected before sending or adding it to conversation history; retype the
message when prompted. If an older image keeps failing after malformed input,
type `clear` to discard that conversation before trying again.

The stage policies cover enrolled boot aggregate and kernel modules. They do
not measure application/model/GPU integrity, attest inference output, or provide
TLS session binding and relay resistance. Verification archives and separate
application decisions remain private in the state volume.

See [the detailed flow](docs/attestation-flow.md) for trust boundaries, identity,
reference pins, saved records and console output; [the policy catalog](profiles/README.md)
for fixture scope; and [operator tooling](tools/README.md) for enrollment.

## Identity implementation and session recovery

The demo uses MSAL Python for Entra CIAM. All integration code stays in `demo/`;
there is no Aditus dependency or additional build context. MSAL owns PKCE, token
exchange, account metadata, and silent acquisition. The application owns its
CIAM settings, account-selection prompts, callback delivery and admission.

MSAL serializes its token cache; MSAL Extensions supplies file persistence and
locking. The Linux image explicitly
uses an unencrypted file in its private state volume, with a `0700` directory,
`0600` cache, and atomic replacement. It does not assume a desktop keychain.
Keep the volume private. The cache is partitioned by client, authority and scopes.
Acquisition and local logoff run under the same cache lock. Cache mutations are
committed only on success: even MSAL's eviction of an expired access token is
rolled back when renewal fails. Temporary failures preserve the previous file
and withhold the application request.
Local logoff removes the selected account from this application's cache.

The previous raw-token `session.json` is not imported. On the first launch after
this update, sign in once again. The old file remains if sign-in is declined or
fails; successful MSAL sign-in removes it. Existing run archives are preserved.

The callback uses `http://localhost:8765` and MSAL's authorization-code `query`
response mode with PKCE. This avoids an HTTPS-to-HTTP form submission prompt in
Safari. Only a one-use code returns through the loopback URL; MSAL exchanges it
for tokens over HTTPS. The landing page clears the query from browser history,
does not reflect the code, and disables referrer forwarding and caching.
Docker publishes it on host loopback only. Sign-in and restored sessions still
require the application's evidence appraisal and HTTPS peer checks before any
Flint API token is forwarded.

The application has no short session timeout. MSAL reuses cached tokens and
silently renews expired tokens, subject to Entra's session and revocation policy.
An API HTTP 401 preserves the saved identity and reports an API rejection; only
MSAL's explicit interaction-required response starts sign-in recovery. API
requests are never automatically replayed. Tests exercise silent recovery over
20 minutes with five-minute tokens and controlled time.

For automated packaged-image checks, build the image, then run from this root:

```sh
python3 scripts/msal_image_checks.py --image confidential-ai-example:local
```

The check uses synthetic identity HTTP responses with the real MSAL library,
a real published callback, and a disposable Docker volume reused across fresh
containers. It checks sign-in, temporary outage, silent renewal after restart,
cached recovery and logoff. It does not establish live Entra compatibility.
For live acceptance of a local build, use a dedicated test volume:

```sh
CONFIDO_IMAGE=confidential-ai-example:local CONFIDO_STATE_VOLUME=confidential-ai-example-msal-live ./run
```

Complete browser sign-in, exit normally, then repeat the same command and continue
without a browser prompt. Also exercise local logoff and a new sign-in. The host
browser must reach the Docker host's localhost port 8765; forward that port when
using a remote Docker host. Live sign-in remains operator-run. The [dated image acceptance](docs/msal-image-acceptance-20261125.md)
records automated results and their limits.

An `unknown` label on Entra's browser account picker is separate from this
console's identity label. Check the external-tenant user's `displayName` and the
user flow's **Display Name** attribute; **Given Name** and **Surname** are separate
fields. If the browser retained an old account label, sign out on the provider's
page and sign in again after correcting the profile. Local demo logoff only
clears the application's token cache. See Microsoft's
[user profile attributes](https://learn.microsoft.com/en-us/entra/external-id/customers/concept-user-attributes).
The [automatic naming contract](docs/entra-display-name.md) describes the required
registration-side change and its pending tenant configuration. Rebuilding the
demo does not update Entra directory profiles.

## Developer checks

The user launch path only pulls and runs an image. Image builds belong to development/CI.
`docker build --platform linux/amd64 -t confidential-ai-example:local .` builds
the final image and requires the application tests to pass against its exact
runtime and wheel. `--target tests` runs only through that test stage.
Enrollment tests run in the
separate reference client project.

To test an unpublished Linux wheel without a host Python installation:

```sh
make build CONFIDO_CLIENT_WHEEL=/absolute/path/to/confido_client-0.2.1a1-cp315-cp315-manylinux_2_34_x86_64.whl
CONFIDO_IMAGE=confidential-ai-example:local ./run
```

`make build` uses Docker and a selected candidate in the ignored `.image-wheel/`
directory. Default builds fetch the upstream wheel inside Linux; host architecture
does not select a macOS/Windows wheel for the image. The Docker context excludes
local environments, caches, credentials and private run archives. Native developers
who already have a prepared `.venv` can also use `make test`.
To update that environment to the pinned client, run
`.venv/bin/python scripts/install_client_wheel.py`; this validates and installs
the upstream wheel and records its origin. Then run
`.venv/bin/python -m demo.runtime` and `make test`. Runtime startup does not
perform this installation.
