# Confidential AI example — Confido verifier 0.2

A client-side demonstration of how an application can use attestation before
sending an application request. In isolated tests, the matching case sends one
synthetic request after evidence and TLS-peer checks; the deliberately
mismatched reference causes the application to deny it. This demonstrates the
decision flow, not the integrity of the application, GPU, model, or inference
runtime. See Confido's
[security model](https://github.com/jandigitrust/confido/blob/main/docs/security-model.md)
for the underlying trust chain and terminology.

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

From the repository root, use Python and `make`. This local revision uses one
`confido-client` 0.2.0 wheel built from the JAN Confido client branch and checked
against [`confido-client-wheel.json`](confido-client-wheel.json). Supply its path
to the first setup; subsequent updates can reuse the staged wheel. The example
does not build Rust code or Confido from source. Attestor and the Flint
gateway run separately at the HTTPS origins in the application policies. The
client needs access to AMD KDS and the GitHub API; both demo names must resolve
to the intended HTTPS frontend from the machine running it.
After admission, chat requests use Flint's `tinyllama-1.1b-chat-v1.0` alias.
Flint runs the corresponding TinyLlama-1.1B-Chat-v1.0 model locally on the
GENXT VM, behind the appraised HTTPS endpoint. The client does not run or
download model weights. The [Flint deployment](https://github.com/genxnetwork/flint)
pins the model conversion and runtime image.

```sh
CONFIDO_CLIENT_WHEEL=/path/to/confido_client-0.2.0-<platform>.whl make dev-setup
make test
make dev-chat-genoa
```

`make dev-chat-genoa` copies the two application policies and their Genoa
verifier policies into the ignored `.artifacts/genoa-console-profiles/` directory,
then runs the interactive client. Once those copies exist, this is equivalent:

```sh
CONFIDO_POLICY_DIR="$PWD/.artifacts/genoa-console-profiles" make dev-chat
```

Use `make dev-chat-genoa` again after editing a source policy so the private
copies are refreshed. Without `CONFIDO_POLICY_DIR`, `make dev-chat` loads the
checked-in Milan verifier policies. `make build` and `make chat` likewise use
the checked-in profiles, not the ignored Genoa copies; they are separate from
this local Genoa command. `make dev-update` reinstalls the pinned wheel when
the application or client changes. Set `CONFIDO_CLIENT_WHEEL` again to replace
the staged candidate. The wheel's distribution, version, embedded source
identities, native binary and Python adapter are checked; its SHA-256 is recorded
in `build/wheel.sha256`. Until a reviewed Confido client wheel is published, the
application deliberately does not download a package by name from an index.
Python dependencies remain pinned in `requirements.lock`. `make build` uses the
staged wheel; it needs no Confido source checkout.

To produce a candidate wheel, use a separate JAN Confido checkout at the
`source_commit` in the pin and run `make -C bindings/client-python wheel`
there with `PYTHON` set to the desired interpreter. The resulting wheel must
match the operating system and Python version of this application.

The [Genoa stage guide](docs/genoa-stage-reference.md) explains reference
enrollment and earlier isolated acceptance with a synthetic downstream. Both
interactive targets update stale development builds before starting the client.

`POST /tee-report` requires no application login. Before retrieval, the console
opens Teraveri Identity's email-OTP sign-in in the system browser, using a public
client and Authorization Code with PKCE. The access token stays in process memory.
After evidence and TLS-peer checks, the scoped transport sends it only to the
appraised `/v1/models` and `/v1/chat/completions` routes. Flint validates the
token at its HTTPS gateway and supplies its separate backend key server-side.
The client never reads an application password or backend API key. Other gateway
routes keep their existing access rules. Local port 8765 must be available for
the browser callback. `make chat` publishes this port only on the host's
loopback address; open the printed sign-in URL on that same host if the
container cannot launch a browser.
The isolated acceptance uses a synthetic downstream.
Decline, sign-in failure, collection failure, mismatched evidence and peer failure
withhold the chat request. A mismatch sends no user access token to the demo VM.
Bootstrap retrieval is unauthenticated; an explicit application-policy option
permits self-signed bootstrap. Confido's client checks the attested certificate's
exact DER, hostname and validity on every connection; other origins and
redirects are rejected. Its transport is reusable across applications, while
this example owns the email sign-in, API route limits and admission decision.

The [profile catalog](profiles/README.md) and [application schemas](schemas/README.md)
explain each demo policy and application decision. Genoa is the AMD EPYC
processor generation of the local test VM; the original Milan demo uses a
different generation and enrollment.
Application profiles contain a locally approved HTTPS origin and a
`verifier_policy` filename.
Verifier policies contain the independently enrolled root, platform and reference.
Match/mismatch use the same verifier code path with different local reference pins.
This repository owns these demo policies. The Genoa stage enrollment inputs and
positive/negative policies also live under `profiles/`; `scripts/enroll_reference.py`
checks the GENXT publisher statement before emitting a pinned positive policy.
The positive reference is a stage candidate in the
[Teraveri registry](https://github.com/teraveri/reference-value-registry); the
negative reference is an unendorsed fixture there, not an alternative trusted
baseline. During each run the Confido client downloads the exact `reference.json`
at the policy's full Git commit and checks its SHA-256 and measurements.
The publisher statement is checked at enrollment, not rechecked on each run.
Neither a registry update nor a new branch tip changes an existing pin. If the
pinned file cannot be retrieved, the application withholds chat.
The browser extension's approved demo origins are in
[`profiles/extension-origins.json`](profiles/extension-origins.json). The GENXT
Nginx routing is maintained by [Flint](https://github.com/genxnetwork/flint).
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
application/model/GPU state, including the local TinyLlama weights and runtime,
are outside that coverage. Local inference does not attest the model or output.
The browser extension in the Confido repository performs evidence checks entirely
in WASM and does not use this transport or send chat prompts.

## Runtime and attestation output

`make dev-chat` checks application sources, the staged wheel hash, and the
**loaded native binary and Python adapter**, then reinstalls stale artifacts in
the selected `VENV`. If no wheel has been staged, supply `CONFIDO_CLIENT_WHEEL`
to `make dev-update` first.
A package version alone does not establish compatibility. `make dev-info` checks
this relationship explicitly; the runtime requires verifier pipeline revision 2.
Containers use an embedded runtime manifest and need no Confido source checkout.
Builds whose sources change mid-build are rejected before publishing a manifest.

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
