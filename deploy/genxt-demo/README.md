# GENXT demo routing

This directory owns the GENXT deployment template and the browser extension's
approved HTTPS origins. Match and mismatch use the same attestation collector and
TLS certificate; their application policies select different pinned references.

| Component | Listener | Public route |
|---|---|---|
| Nginx TLS terminator | 443 | `/tee-report`, `/v1/...` |
| Nginx redirect | 80 | 308 to same-host HTTPS |
| Confido collector | 127.0.0.1:8001 | POST `/tee-report`, HEAD `/tee-report` |
| Flint | 127.0.0.1:4000 | application API |

The caller sends a fresh 32-byte base64 nonce in a JSON POST body. The collector
returns the report and its quote-bound certificate with `Cache-Control: no-store`.
The caller verifies the report against its local policy, then sends a credentialless
HEAD request to the same endpoint using a TLS client pinned to that certificate.
Only after a 204 response may it release application credentials. This verifies
the intended HTTPS peer; it does not bind the report to the TLS session.

Both names must appear in `/etc/confido/certificate.pem` SANs. The matching
private key is `/etc/confido/private_key.pem`, mode 0600. Install the reviewed
collector binary as `/usr/local/bin/confido-server`. Generate the local Basic
Auth and gateway-key includes using the Flint operator instructions; keep those
secret files outside Git. `/aTLS` returns 404 and private backend ports stay
loopback-only.

Build the browser extension from the sibling Confido checkout with
`--origins-config ../confidential-ai-example/deploy/genxt-demo/extension-origins.json`.
Without that file the generic extension has no live origins. The browser
extension verifies evidence only and does not authenticate the TLS peer against
the attested certificate or admit application traffic.

Run `scripts/preflight.py` before promotion; pass `--flint` when comparing a
prepared Flint checkout against this Nginx template. Stage and test revised
versions on isolated ports first. Historical baseline identifiers remain in
the prior Confido revision commit history.
