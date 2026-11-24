# Example support scripts

These scripts support local client builds, reference enrollment, and explicit
client checks. Start the current Genoa console from the repository root with
`make dev-chat-genoa`; plain `make dev-chat` uses the checked-in Milan policies
unless `CONFIDO_POLICY_DIR` selects prepared Genoa policies.

| Script | Purpose |
| --- | --- |
| [`source_fingerprint.py`](source_fingerprint.py) | Hashes selected application and transport source inputs. |
| [`build_wheels.py`](build_wheels.py), [`install_wheels.py`](install_wheels.py) | Prepare each project's licences, then build, fingerprint and install the two local wheel artifacts. |
| [`build_manifest.py`](build_manifest.py) | Records wheel and container identity. |
| [`dev_info.py`](dev_info.py), [`ensure_runtime.py`](ensure_runtime.py) | Inspect the loaded runtime and rebuild stale development artifacts. |
| [`enroll_reference.py`](enroll_reference.py) | Verify a registry publisher statement and emit a locally pinned verifier policy. |
| [`preflight.py`](preflight.py) | Check the installed client and optionally its external attestation endpoint. |
| [`container_acceptance.py`](container_acceptance.py) | Exercise the client inside a prepared container against an external endpoint. |
| [`browser_live_checks.py`](browser_live_checks.py) | Opt-in live browser-extension check against the public demo endpoint. |

The [root README](../README.md) covers development commands. The
[Genoa stage guide](../docs/genoa-stage-reference.md) documents the pinned
reference enrollment. The optional isolated acceptance harness lives in
[Attestor](https://github.com/jandigitrust/attestor/tree/main/integration).
