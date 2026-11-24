# Application flow

This package owns the example application's collection, presentation, TLS
transport, and admission decision. Confido verifies evidence bytes; the
application decides whether to use an appraised endpoint and when a chat request
may be sent. Start the current Genoa flow with `make dev-chat-genoa` from the
repository root. Plain `make dev-chat` uses the checked-in Milan policies unless
`CONFIDO_POLICY_DIR` points to prepared Genoa policies.

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
