# Application tests

`make test` from the repository root runs these Python tests and the Rust
unit tests in `native_transport/`. The Python suite uses local fixtures and
mocked dependencies; its transport test opens a disposable localhost listener.
Live Genoa and browser acceptance are separate commands under `scripts/`.

| File | Focus |
| --- | --- |
| [`test_collection.py`](test_collection.py) | Bounded retrieval and verifier inputs. |
| [`test_admission.py`](test_admission.py) | Credential gating and application decisions. |
| [`test_run.py`](test_run.py) | One-use live context and archive limits. |
| [`test_transport.py`](test_transport.py) | TLS peer and reconnect behavior. |
| [`test_runtime.py`](test_runtime.py) | Loaded wheel and source identity. |
| [`test_enroll_reference.py`](test_enroll_reference.py) | Publisher statement and local policy enrollment. |
| [`test_attestation_log.py`](test_attestation_log.py) | User-facing result presentation. |
