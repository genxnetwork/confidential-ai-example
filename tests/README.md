# Application tests

The Docker `tests` stage uses the runtime dependency lock and runs
the application suite. The final image copies a success marker from this stage,
so building the final image requires tests of its exact runtime and wheel to pass.
CI also exercises the launch wrappers on Linux, macOS and
Windows with a Docker CLI stub, without requiring a local daemon for those tests.
The Confido client has its own Rust/Python tests; live admission is separate.

`docker build --platform linux/amd64 --target tests .` uses the latest compatible
upstream client wheel. Native developers with a prepared `.venv` can use `make test`.

| File | Focus |
| --- | --- |
| [`test_policy.py`](test_policy.py) | Local application and verifier policy loading. |
| [`test_client_wheel.py`](test_client_wheel.py) | Confido client wheel metadata and package requirements. |
| [`test_download_client_wheel.py`](test_download_client_wheel.py) | Latest successful GitHub build selection and artifact integrity. |
| [`test_admission.py`](test_admission.py) | Credential gating, safe errors, session recovery and CLI failure exit status. |
| [`test_identity_transport.py`](test_identity_transport.py) | Email sign-in and permitted API routes. |
| [`test_identity.py`](test_identity.py) | Actual MSAL PKCE/exchange, private cache, renewal failures, restart recovery, migration and local logoff. |
| [`test_run.py`](test_run.py) | Shell/PowerShell image reuse, callback/state mapping, update and Docker errors. |
| [`test_runtime.py`](test_runtime.py) | Public client API and verifier pipeline compatibility. |

For runtime-only native checks, use `.venv/bin/python -m unittest discover -s tests -v`.
Enrollment tests and Python cryptography moved to `../../sanctio/`.

`test_identity_callback.py` exercises bounded form callbacks, state filtering,
browser preconnections and the sign-in deadline. `identity_provider.py` supplies
synthetic HTTP responses to the real MSAL library. The opt-in packaged-image
check is documented in the root README and uses `identity_image_probe.py` across
fresh containers. These fixtures never use live credentials.
