# Application tests

`make test` from the repository root runs application Python tests with local
fixtures and mocked dependencies. The Confido client has its own Rust and Python
tests in JAN Confido; live Genoa and browser acceptance are separate checks.

| File | Focus |
| --- | --- |
| [`test_policy.py`](test_policy.py) | Local application and verifier policy loading. |
| [`test_client_wheel.py`](test_client_wheel.py) | Confido client wheel metadata and package requirements. |
| [`test_admission.py`](test_admission.py) | Credential gating and application decisions. |
| [`test_identity_transport.py`](test_identity_transport.py) | Email sign-in and permitted API routes. |
| [`test_runtime.py`](test_runtime.py) | Loaded wheel and source identity. |
| [`test_enroll_reference.py`](test_enroll_reference.py) | Publisher statement and local policy enrollment. |
| [`test_attestation_log.py`](test_attestation_log.py) | User-facing result presentation. |
