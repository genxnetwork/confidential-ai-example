# Application flow

This package owns the example application's local policy, email sign-in,
presentation, token routing and admission decision. The installed Confido client
retrieves and appraises evidence and authenticates the HTTPS peer. The application
decides whether and when a chat request may be sent. Start the Genoa flow with `./run` (Linux/macOS) or `.\run.cmd` (Windows).
Both run the same Linux image. The launchers persist state in a Docker volume
and can mount an explicit host `GENXT_DEMO_POLICY_DIR` read-only.

| Module | Role |
| --- | --- |
| [`policy.py`](policy.py) | Loads local application and verifier policies. |
| [`identity.py`](identity.py) | Configures MSAL and its private cache; owns account selection, sign-in prompts and local logoff UX. |
| [`identity_callback.py`](identity_callback.py) | Delivers a bounded Docker loopback callback to MSAL. |
| [`transport.py`](transport.py) | Limits the token to allowed API routes over Confido's origin-scoped transport. |
| [`admission.py`](admission.py) | Applies the caller's decision after evidence and peer checks. |
| [`runtime.py`](runtime.py) | Checks the installed public client API and verifier pipeline. |

The [root README](../README.md) describes the complete flow and local setup.
Detailed verification output is provided by `confido_client.console`; this
example prints its separate application admission decision.
Demo policies and reference pins live under [`profiles/`](../profiles/README.md).
