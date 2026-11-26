# Confidential AI example

A console demo that verifies attestation evidence and authenticates the HTTPS
peer before sending a chat request. The application selects a local policy,
uses [JAN Confido](https://github.com/jandigitrust/confido) for evidence and peer
checks, and makes its own admission decision.

The supplied Genoa stage policies cover the VM's enrolled boot aggregate and
kernel modules. They do not attest application code, the model, GPU state or
inference output. Inference runs outside the appraised VM. TLS session binding
and relay resistance are unsupported. See the
[attestation flow](docs/attestation-flow.md) and Confido's
[security model](https://github.com/jandigitrust/confido/blob/main/docs/security-model.md)
for the trust boundaries. This is a development and staging example using an
alpha SDK; production use is unsupported.

## Run the demo

Install and start Docker with Linux containers. On macOS and Windows, use Docker
Desktop. The image targets `linux/amd64`; Apple Silicon uses Docker's architecture
emulation. Host Python, Rust and model weights are not required. Host loopback
port 8765 must be available for browser sign-in.

Linux / macOS:

```sh
./run
```

Windows PowerShell or Command Prompt:

```powershell
.\run.cmd
```

The launcher uses the selected local image if present, otherwise pulls it.
The default image is `ghcr.io/genxnetwork/confidential-ai-example:latest`.
To run a local build or another published tag, set `CONFIDO_IMAGE` as described
below. Registry pulls require that the selected tag exists and is accessible.

1. Sign in through Teraveri Identity. The launcher opens the host browser when
   sign-in is needed; the console provides a link if automatic opening fails.
2. Select **match** to use the matching stage policy or **mismatch** to exercise
   rejection against a deliberately incompatible reference.
3. Permit evidence retrieval. Chat opens only after successful evidence
   verification and HTTPS peer authentication. Declining or failing either
   check withholds the chat request.
4. In chat, enter `clear` to reset the conversation, or `exit` / `quit` to return
   to endpoint selection. Select `0` at endpoint selection to exit.

The client uses a preconfigured OpenAI-compatible chat service. Replies are
buffered and capped at 256 generated tokens with a concise-answer prompt.
The client allows 30 seconds per request and does not automatically retry failures.
Long prompts or slow generation can time out. Malformed UTF-8 input is rejected
before sending or adding it to conversation history.

Browser opening uses `open` on macOS or `xdg-open` on Linux, with `curl` for the
local handoff; Windows uses its default URL handler. Set `CONFIDO_BROWSER=manual`
to use the printed link. The browser must reach the Docker host at
`http://localhost:8765`, including when Docker runs remotely.

## Session and settings

The named Docker volume `confidential-ai-example-state` stores sign-in state and
private verification archives. Restarting or changing the image preserves this
volume. At startup, a saved identity offers continue or local logoff. Local
logoff removes that account from the application's cache, without signing out
other browser applications.

MSAL silently renews tokens when possible. Temporary identity-service failures
preserve the saved session and withhold the request. An API HTTP 401 also
preserves sign-in and reports the rejection. Only the admitted `/v1/models` and
`/v1/chat/completions` routes receive the user's access token.

The cache is an unencrypted file inside the private state volume, with `0700`
directories and `0600` files. Keep the volume private. Browser sign-in uses an
authorization code with PKCE through the loopback callback; the landing page
clears the query from browser history and sends no referrer.

| Setting | Purpose | Default |
| --- | --- | --- |
| `CONFIDO_IMAGE` | Select a local image or published tag. | `ghcr.io/genxnetwork/confidential-ai-example:latest` |
| `CONFIDO_STATE_VOLUME` | Select a separate Docker state volume. | `confidential-ai-example-state` |
| `CONFIDO_POLICY_DIR` | Mount an application policy directory read-only. | Genoa stage policies packaged in the image. |
| `CONFIDO_BROWSER` | Choose `auto` or `manual` browser opening. | `auto` |
| `CONFIDO_COLOR` | Choose `always`, `auto` or `never` for console colors. | `auto` |

`./run --setup` ensures the selected image is available without signing in.
`./run --info` shows its Confido version and build information without networking
inside the container. `./run --update` pulls the selected image and shows its
build information. The same options work with `.\run.cmd` on Windows.
Use an explicit image selection consistently, including for `--info`.

For example, with a local image:

```sh
CONFIDO_IMAGE=confidential-ai-example:local ./run --info
CONFIDO_IMAGE=confidential-ai-example:local ./run
```

## Build and verify

From the repository root, build the client image:

```sh
docker build --platform linux/amd64 -t confidential-ai-example:local .
```

The final image depends on the Docker test stage passing against its exact
runtime and installed Confido wheel. `--target tests` builds through that stage
without producing the final image. Rebuild a local image to incorporate source
changes; ordinary launches reuse the selected image.

Image builds select the latest successful main-branch `Client wheel` push build
from JAN Confido, check the downloaded archive SHA-256 against GitHub metadata,
and validate the wheel against [`confido-client-wheel.json`](confido-client-wheel.json).
Missing, expired or incompatible artifacts stop the build. Startup checks the
installed client APIs, Python 3.15 and verifier pipeline 2 without installing
dependencies. `--info` also shows installation provenance when available.

To build with an explicit compatible Linux wheel:

```sh
make build CONFIDO_CLIENT_WHEEL=/absolute/path/to/confido_client-0.2.1a1-cp315-cp315-manylinux_2_34_x86_64.whl
```

In a prepared native environment, `make test` runs the application suite.
The [scripts guide](scripts/README.md) covers dependency installation and
preflight helpers; the [tests guide](tests/README.md) explains test scope.

Check packaged identity recovery with synthetic provider responses:

```sh
python3 scripts/msal_image_checks.py --image confidential-ai-example:local
```

For live browser and chat checks, use a dedicated state volume:

```sh
CONFIDO_IMAGE=confidential-ai-example:local CONFIDO_STATE_VOLUME=confidential-ai-example-review ./run
```

Exercise match, mismatch, restart recovery and logoff using the
[reviewer checklist](docs/attestation-flow.md#reviewer-checks). Synthetic checks
exercise application boundaries; live identity and service compatibility require
that separate browser-driven check.

The image workflow tests launchers on Linux, macOS and Windows, builds and tests
the Linux image, checks packaged identity recovery, and publishes the checked
image on push. The default branch supplies `latest`; other branches receive
branch and commit tags. Publication requires successful CI and registry access.

The [application guide](demo/README.md), [policy catalog](profiles/README.md), and
[schema catalog](schemas/README.md) describe the maintained client interfaces.
