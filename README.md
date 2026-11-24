# Confidential AI example — Confido verifier 0.2

A client-side demonstration of how an application can use attestation before
sending an application request. In isolated tests, the matching case sends one
synthetic request after evidence and TLS-peer checks; the deliberately
mismatched reference causes the application to deny it. This demonstrates the
decision flow, not the integrity of the application, GPU, model, or inference
runtime. See Confido's
[security model](https://github.com/jandigitrust/confido/blob/main/docs/security-model.md)
for the underlying trust chain and terminology.

A cooperating native client separates evidence verification from transport and
application admission. `demo/collection.py` retrieves raw inputs; `confido_verifier`
checks bytes and local policy; `native_transport/` authenticates the actual TLS
peer; `demo/admission.py` checks the attestation endpoint over that TLS connection
before the chat client is opened.
The sibling [Attestor](https://github.com/jandigitrust/attestor) checkout provides
native evidence collection and `POST /tee-report`.
The component guides cover [`demo/`](demo/README.md),
[`native_transport/`](native_transport/README.md),
[`scripts/`](scripts/README.md), and [`tests/`](tests/README.md).

## Current Genoa demo

From the repository root, use the `main` branch of [JAN Confido](https://github.com/jandigitrust/confido)
as a sibling source checkout at `../confido/lib` (or set `CONFIDO_LIB`), plus
Python, Rust/Cargo, and `make`. Attestor and the Flint
gateway run separately at the HTTPS origins in the application policies. The
client needs access to AMD KDS and the GitHub API; both demo names must resolve
to the intended HTTPS frontend from the machine running it.
After admission, chat requests use Flint's `tinyllama-1.1b-chat-v1.0` alias.
Flint runs the corresponding TinyLlama-1.1B-Chat-v1.0 model locally on the
GENXT VM, behind the appraised HTTPS endpoint. The client does not run or
download model weights. The [Flint deployment](https://github.com/genxnetwork/flint)
pins the model conversion and runtime image.

```sh
make dev-setup
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
this local Genoa command. `make dev-update` explicitly rebuilds both wheels.

Local wheel builds require JAN Confido source. The Makefile uses a sibling checkout
at `../confido/lib` by default; set `CONFIDO_LIB` only if that source is elsewhere.
The installed client and built container do not need a Confido checkout. Two
independently hashed wheels are installed: `confido-verifier` 0.2.0 and
`confai-transport` 0.2.0. Dependencies remain pinned in `requirements.lock`.
`make build` consumes those exact wheel hashes. No package publication is needed.

The [Genoa stage guide](docs/genoa-stage-reference.md) explains reference
enrollment and earlier isolated acceptance with a synthetic downstream. Both
interactive targets update stale development builds before starting the client.

`POST /tee-report` requires no application login. This client does not read or
send an application username, password or API key. Flint accepts `/v1/models`
and `/v1/chat/completions` without Basic authentication from any VM and supplies
its backend key server-side. Other gateway routes keep their existing access rules.
The isolated acceptance uses a synthetic downstream.
Decline, collection failure, mismatched evidence and peer failure withhold the
chat request. Bootstrap retrieval is unauthenticated; an explicit
application-policy option permits self-signed bootstrap. The app-owned
Rust/rustls adapter checks the attested certificate's exact DER, hostname and
validity on every connection; other origins and redirects are rejected. This
adapter does not import the evidence verifier.

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
baseline. During each run the application downloads the exact `reference.json`
at the policy's full Git commit; Confido checks its SHA-256 and measurements.
The publisher statement is checked at enrollment, not rechecked on each run.
Neither a registry update nor a new branch tip changes an existing pin. If the
pinned file cannot be retrieved, the application withholds chat.
The browser extension's approved demo origins are in
[`profiles/extension-origins.json`](profiles/extension-origins.json). The GENXT
Nginx routing is maintained by [Flint](https://github.com/genxnetwork/flint).
The generic verifier accepts policy bytes supplied by its caller and does not
choose these trust pins.
The caller sends a nonce directly to `POST /tee-report`; no metadata discovery
selects the report endpoint or a reference. After evidence appraisal, an
unauthenticated `HEAD /tee-report` over quote-bound certificate-pinned TLS
authenticates the intended peer before the application sends a request.
The run directory holds a v2 verification archive, `.runtime.json` with build metadata
and collection/verification timings, and a separate `.decision.json`;
only the latter contains `application_admitted`.

The quote binds nonce, certificate and IMA log. There is no TLS session binder or
relay-resistance claim. Coverage is enrolled boot aggregate/kernel modules;
application/model/GPU state, including the local TinyLlama weights and runtime,
are outside that coverage. Local inference does not attest the model or output.
The browser extension in the Confido repository performs evidence checks entirely
in WASM and does not use this transport or send chat prompts.

## Runtime and attestation output

`make dev-chat` checks current sources, local wheel hashes and the **loaded native
binary**, then rebuilds and reinstalls stale artifacts in the selected `VENV`.
A package version alone does not establish compatibility. `make dev-info` checks
this relationship explicitly; the runtime requires verifier pipeline revision 2.
Containers use an embedded runtime manifest and need no sibling source checkout.
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
