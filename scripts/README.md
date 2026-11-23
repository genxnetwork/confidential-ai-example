# Example support scripts

These scripts support local builds, deployment checks, reference enrollment,
and explicit acceptance runs. The interactive application is started from
the repository root with `make dev-chat`.

| Script | Purpose |
| --- | --- |
| [`source_fingerprint.py`](source_fingerprint.py) | Hashes selected application and transport source inputs. |
| [`build_wheels.py`](build_wheels.py), [`install_wheels.py`](install_wheels.py) | Prepare each project's licences, then build, fingerprint and install the two local wheel artifacts. |
| [`build_manifest.py`](build_manifest.py) | Records wheel and container identity. |
| [`dev_info.py`](dev_info.py), [`ensure_runtime.py`](ensure_runtime.py) | Inspect the loaded runtime and rebuild stale development artifacts. |
| [`enroll_reference.py`](enroll_reference.py) | Verify a registry publisher statement and emit a locally pinned verifier policy. |
| [`preflight.py`](preflight.py) | Read-only check of deployment configuration and installed packages. |
| [`stage_demo.py`](stage_demo.py), [`container_acceptance.py`](container_acceptance.py) | Isolated hardware-backed and container acceptance flows. |
| [`browser_live_checks.py`](browser_live_checks.py) | Opt-in live browser-extension check against the public demo endpoint. |

The [root README](../README.md) covers development commands. The
[Genoa stage guide](../docs/genoa-stage-reference.md) documents the pinned
reference enrollment and isolated acceptance command.
