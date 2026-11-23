# Application flow

This package owns the example application's collection, presentation, TLS
transport, and admission decision. Confido verifies evidence bytes; the
application decides whether to use an appraised endpoint and when credentials
may be read. Start the interactive flow with `make dev-chat` from the
repository root.

| Module | Role |
| --- | --- |
| [`collection.py`](collection.py) | Retrieves bounded attestation inputs and invokes the installed verifier. |
| [`run.py`](run.py) | Holds the one-use live context; a saved archive cannot recreate it. |
| [`transport.py`](transport.py) | Wraps the origin-scoped [native TLS adapter](../native_transport/). |
| [`admission.py`](admission.py) | Applies the caller's decision after evidence and peer checks. |
| [`runtime.py`](runtime.py) | Checks the loaded native packages against the checkout and build manifests. |
| [`attestation_log.py`](attestation_log.py) | Renders check results for the user without performing verification. |

The [root README](../README.md) describes the complete flow and local setup.
Demo policies and reference pins live under [`profiles/`](../profiles/README.md).
