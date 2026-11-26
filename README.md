# Trustworthy AI – Verifiable and Confidential

## Prototype Demo

A console demo that verifies attestation evidence and authenticates the HTTPS
peer before sending a chat request. The application selects a local policy,
uses [Confido](https://github.com/jandigitrust/confido) for evidence and peer
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
docker build --platform linux/amd64 -t confidential-ai-example:local .
GENXT_DEMO_IMAGE=confidential-ai-example:local ./run
```

Windows PowerShell:

```powershell
docker build --platform linux/amd64 -t confidential-ai-example:local .
$env:GENXT_DEMO_IMAGE = "confidential-ai-example:local"
.\run.cmd
```

Run these commands from the repository root. The build uses the selected
checkout and runs the application tests before producing the local image.
Rebuild that image after updating the source.

The launcher uses the selected local image if present, otherwise pulls it.
`GENXT_DEMO_IMAGE` can also select an accessible published tag. Without that
setting, the launcher requests
`ghcr.io/genxnetwork/confidential-ai-example:latest`; that tag is the publication
target for the default branch. Registry pulls require that the selected tag
exists and is accessible.

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
local handoff; Windows uses its default URL handler. Set `GENXT_DEMO_BROWSER=manual`
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
| `GENXT_DEMO_IMAGE` | Select a local image or published tag. | `ghcr.io/genxnetwork/confidential-ai-example:latest` |
| `GENXT_DEMO_STATE_VOLUME` | Select a separate Docker state volume. | `confidential-ai-example-state` |
| `GENXT_DEMO_POLICY_DIR` | Mount an application policy directory read-only. | Genoa stage policies packaged in the image. |
| `GENXT_DEMO_BROWSER` | Choose `auto` or `manual` browser opening. | `auto` |
| `CONFIDO_COLOR` | Choose `always`, `auto` or `never` for console colors. | `auto` |

`./run --setup` ensures the selected image is available without signing in.
`./run --info` shows its Confido version and build information without networking
inside the container. `./run --update` pulls the selected image and shows its
build information. The same options work with `.\run.cmd` on Windows.
Use an explicit image selection consistently, including for `--info`.

For example, with a local image:

```sh
GENXT_DEMO_IMAGE=confidential-ai-example:local ./run --info
GENXT_DEMO_IMAGE=confidential-ai-example:local ./run
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
from Confido, check the downloaded archive SHA-256 against GitHub metadata,
and validate the wheel against [`confido-client-wheel.json`](confido-client-wheel.json).
Missing, expired or incompatible artifacts stop the build. Startup checks the
installed client APIs, Python 3.15 and verifier pipeline 2 without installing
dependencies. `--info` also shows installation provenance when available.

To build with an explicit compatible Linux wheel:

```sh
make build GENXT_DEMO_CLIENT_WHEEL=/absolute/path/to/confido_client-0.2.1a1-cp315-cp315-manylinux_2_34_x86_64.whl
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
GENXT_DEMO_IMAGE=confidential-ai-example:local GENXT_DEMO_STATE_VOLUME=confidential-ai-example-review ./run
```

Exercise match, mismatch, restart recovery and logoff using the
[reviewer checklist](docs/attestation-flow.md#reviewer-checks). Synthetic checks
exercise application boundaries; live identity and service compatibility require
that separate browser-driven check.

The manually triggered image workflow tests launchers on Linux, macOS and
Windows, builds and tests the Linux image, checks packaged identity recovery,
and publishes the checked image. A separate job pulls the full-commit tag
anonymously, checks that it matches the tested image, and verifies its installed
runtime.
The default branch supplies `latest`. Branch tags use the `branch-` prefix;
commit tags use `sha-` followed by the full commit SHA. Publication requires
successful CI and registry access. Public pulls require a public GHCR package.

The [application guide](demo/README.md), [policy catalog](profiles/README.md), and
[schema catalog](schemas/README.md) describe the maintained client interfaces.

## Infrastructure acknowledgement

Computational infrastructure is provided by
[JAN DIGITRUST](https://www.jandigitrust.org/) under a collaboration consortium
agreement with IIAP NAS RA and GENXT.
