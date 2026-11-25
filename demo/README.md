# Application flow

This package owns the example application's local policy, email sign-in,
presentation, token routing and admission decision. The installed Confido client
retrieves and appraises evidence and authenticates the HTTPS peer. The application
decides whether and when a chat request may be sent. Start the Genoa flow with
`make dev-chat-genoa` from the
repository root. Plain `make dev-chat` uses the checked-in Milan policies unless
`CONFIDO_POLICY_DIR` points to prepared Genoa policies.

| Module | Role |
| --- | --- |
| [`policy.py`](policy.py) | Loads local application and verifier policies. |
| [`identity.py`](identity.py) | Performs the user's email-OTP sign-in. |
| [`transport.py`](transport.py) | Limits the token to allowed API routes over Confido's origin-scoped transport. |
| [`admission.py`](admission.py) | Applies the caller's decision after evidence and peer checks. |
| [`runtime.py`](runtime.py) | Checks the installed client wheel and application sources against the runtime manifest. |
| [`attestation_log.py`](attestation_log.py) | Renders check results for the user without performing verification. |

The [root README](../README.md) describes the complete flow and local setup.
Demo policies and reference pins live under [`profiles/`](../profiles/README.md).
