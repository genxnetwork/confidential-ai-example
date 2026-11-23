# Application TLS transport

This PyO3/Rust package builds `confai-transport`. It provides an
origin-scoped HTTPS client whose TLS peer must present the exact certificate
bound to the appraised evidence and the expected hostname. The package does
not appraise evidence or decide application admission.

| File | Role |
| --- | --- |
| [`src/lib.rs`](src/lib.rs) | Certificate checks, scoped requests, Python interface, and focused Rust tests. |
| [`build.rs`](build.rs) | Stamps source identity and build metadata. |
| [`Cargo.toml`](Cargo.toml), `Cargo.lock`, [`pyproject.toml`](pyproject.toml) | Locked Rust dependencies and Python wheel metadata. |

From the repository root, `make dev-update` builds and installs this wheel
alongside the Confido verifier; `make test` runs the native unit tests and
the application test suite. The reconnect/rotated-certificate boundary is
covered by [`tests/test_transport.py`](../tests/test_transport.py).
