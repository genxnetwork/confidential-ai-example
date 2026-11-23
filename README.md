# Confidential AI example — Confido verifier 0.2

A cooperating native client separates evidence verification from transport and
application admission. `demo/collection.py` retrieves raw inputs; `confido_verifier`
checks bytes and local policy; `native_transport/` authenticates the actual TLS
peer; `demo/admission.py` checks the attestation endpoint over that TLS connection
before credentials are read.
The component guides cover [`demo/`](demo/README.md),
[`native_transport/`](native_transport/README.md),
[`scripts/`](scripts/README.md), and [`tests/`](tests/README.md).

## Local development

```sh
make dev-setup
make test
make dev-chat
# Explicitly rebuild both wheels (dev-chat also updates stale builds):
make dev-update
# Optional local container build:
make build
```

The sibling Confido checkout defaults to `../confido/lib`; override `CONFIDO_LIB`
if needed. Two independently hashed wheels are installed: `confido-verifier`
0.2.0 and `confai-transport` 0.2.0. Dependencies remain pinned in requirements.lock.
`make build` consumes those exact wheel hashes. No package publication is needed.

Configure `CONFIDO_USERNAME`/`CONFIDO_PASSWORD` or a private `.credentials.json`.
The program reads them only after verification and the pinned TLS peer check.
Decline, collection failure, mismatched evidence and peer failure withhold chat.
Bootstrap retrieval is credentialless; self-signed bootstrap is an explicit native
application-policy option. Exact attested DER, hostname and validity are checked
by the app-owned Rust/rustls adapter on every connection; other origins and
redirects are rejected. This adapter does not import the evidence verifier.

The [profile catalog](profiles/README.md) explains each demo and Genoa stage
policy. Application profiles contain a locally approved HTTPS origin and a
`verifier_policy` filename.
Verifier policies contain the independently enrolled root, platform and reference.
Match/mismatch use the same verifier code path with different local reference pins.
This repository owns these demo policies. The Genoa stage enrollment inputs and
positive/negative policies also live under `profiles/`; `scripts/enroll_reference.py`
verifies the registry publisher statement and emits a pinned verifier policy.
The reference bytes and publisher statements remain in their own registries.
The GENXT routing and browser-extension host configuration is under
`deploy/genxt-demo/`. The generic verifier accepts policy bytes supplied by its
caller and does not choose these trust pins.
The caller sends a nonce directly to `POST /tee-report`; no metadata discovery
selects the report endpoint or a reference. After evidence appraisal, a
credentialless `HEAD /tee-report` over quote-bound certificate-pinned TLS
authenticates the intended peer before application credentials are read.
The run directory holds a v2 verification archive, `.runtime.json` with build metadata
and collection/verification timings, and a separate `.decision.json`;
only the latter contains `application_admitted`.

The quote binds nonce, certificate and IMA log. There is no TLS session binder or
relay-resistance claim. Coverage is enrolled boot aggregate/kernel modules;
application/model/GPU state and external Azure inference are outside that coverage.
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
entries appear immediately before the IMA comparison verdict, with compact hashes.
An early failure still shows the received entries, explicitly unverified. The
archive retains full values. Successful labels use ANSI green 32; endpoint details
use dark gray. `CONFIDO_COLOR=always|auto|never` controls terminal color.

The final summary separates evidence verification from application admission.
The 120-second monotonic challenge deadline is checked again after rendering and
the pinned TLS peer check. A live run is one-use; loading an old archive cannot
restore it. An expired run or a failed TLS peer never releases credentials.
