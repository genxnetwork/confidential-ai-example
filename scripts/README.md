# Image build and development helpers

Users run `./run` or `.\run.cmd`, which pull a ready image and invoke Docker.
These Python helpers run inside image builds or developer environments.

| Script | Purpose |
| --- | --- |
| [`download_client_wheel.py`](download_client_wheel.py) | Select the latest successful Confido client build and verify its archive SHA-256. |
| [`install_client_wheel.py`](install_client_wheel.py) | Validate/install that wheel or a selected candidate; record provenance after success. |
| [`preflight.py`](preflight.py) | Check client compatibility and optionally an external attestation endpoint. |
| [`live_acceptance.py`](live_acceptance.py) | Opt-in admission check against an isolated synthetic downstream. |

`./run --info` inspects the installed client inside the image. The
[root README](../README.md) covers launch commands and local image builds;
the [policy catalog](../profiles/README.md) describes the selected Genoa reference pins.

`msal_image_checks.py --image IMAGE` runs opt-in packaged identity checks using
synthetic CIAM HTTP responses, the real MSAL library, a host-loopback callback
and a disposable Docker state volume. See the root README for scope and the
separate live browser sign-in procedure. It does not publish an image.
