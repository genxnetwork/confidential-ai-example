# GENXT demo routing and installation

This directory owns the two-service demonstration configuration: `nginx.conf`,
`systemd-confido.service`, `match-demo.yaml`, `mismatch-demo.yaml`, and
`extension-services.json`. The current Flint checkout also has a deployed
copy of the Nginx configuration; `scripts/preflight.py` checks that it matches
this source before promotion. The sidecar repository still contains historical
copies of the two YAML files. New demo changes should be made here first.

| Component | Listener | Public route |
|---|---|---|
| Nginx TLS terminator | 443 | `/service-info`, `/tee-report`, `/v1/...` |
| Nginx redirect | 80 | 308 to same-host HTTPS |
| Confido | 127.0.0.1:8001 | POST `/tee-report` |
| Match sidecar | 127.0.0.1:8082 | GET `/service-info` |
| Mismatch sidecar | 127.0.0.1:8083 | GET `/service-info` |
| Flint | 127.0.0.1:4000 | application API |

Both names must appear in `/etc/confido/certificate.pem` SANs. The matching private key is `/etc/confido/private_key.pem`, mode 0600. The collector checks key correspondence and its configured hostname at startup. A newly generated certificate has only the explicitly supplied hostname: provision a two-SAN certificate before starting the public two-name deployment. Keep metrics loopback-only as configured in sidecar `deploy/systemd/*.env.example`.

Install the reviewed binary as `/usr/local/bin/confido-server`; the unit never runs a build-directory binary. Install sidecar 0.3.0 advertisement support and both config files together. Copy the canonical Nginx file after generating the local Basic Auth and gateway-key includes using the Flint operator instructions. Do not commit those secret files. `/aTLS` returns 404; no service listens publicly on 8000/8001/8082/8083.

Build the browser extension from the sibling Confido checkout with
`--services-config ../confidential-ai-example/deploy/genxt-demo/extension-services.json`.
Without this file the generic extension has no live service hosts.

Run the application's `scripts/preflight.py` before promotion and preserve
its output. Stage and test revised versions on isolated ports first. Review
the changed certificate and policy identities before replacing a running
installation. Historical baseline identifiers remain in
`../../../confido/docs/revision/checkpoint.json`.
