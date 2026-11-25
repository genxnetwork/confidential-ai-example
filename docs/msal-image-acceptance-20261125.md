# Packaged MSAL acceptance — 2026-11-25 UTC

The demo now uses MSAL Python 1.39.0 and MSAL Extensions 1.3.1. Integration stays
inside `demo/`; the Aditus source dependency and custom OAuth implementation have
been removed. This is local implementation acceptance, not a published release.

## Tested artifact

- Platform: Linux x86_64, CPython 3.15.2.
- Local image: `confidential-ai-example:msal`.
- Image ID: `sha256:08cf2787f20cfeda1ff94c7a31b0be0a41b6c432287f2086441f89b7106f5d17`.
- Base: the digest-pinned Python image in the Dockerfile.
- Explicit local Confido candidate: `confido_client-0.2.0-cp315-cp315-manylinux_2_34_x86_64.whl`.
- Candidate SHA-256: `d92f491cc7a45e46b48630373a6aad529ee4375917431fefb28a3dd75a3d8006`.
- Source was a modified local working tree. The hashes below identify relevant
  inputs; they are not publisher authentication or a provenance attestation.

## Observed results

| Check | Result and scope |
| --- | --- |
| `make test` | 45 tests passed. |
| Docker build of the final target | Succeeded; this builder also executed the tests stage, with all 45 tests passing inside the packaged environment. |
| `python3 -m pip check` in the final image | No broken requirements. |
| Actual MSAL auth-code flow at synthetic HTTP boundary | PKCE, requested scopes, code exchange and account selection passed. State/nonce failures committed no credentials. |
| Published callback port | A real host-loopback form POST reached the receiver inside the image and completed synthetic sign-in through MSAL. |
| Fresh container during simulated HTTP 503 renewal outage | Operation failed safely; the persisted cache remained byte-for-byte unchanged. |
| Fresh container after restoration | Silent refresh used the persisted refresh token without opening an interactive callback. |
| Another fresh container | Reused the recovered access-token cache without a token-endpoint request. |
| Local logoff | Removed the selected application's account; reopening the cache found no accounts. |
| Competing refresh/logoff in both orders | Locking and reload prevented a stale client from restoring logged-off credentials. |
| Flint request boundary | Evidence mismatch and peer failure sent no application request; successful path ordered appraisal, peer check, token acquisition and request. |
| Public CIAM discovery from final image | MSAL initialized the configured `teraveri.ciamlogin.com` authority using isolated temporary state and normal TLS validation. |

The cross-container check used the actual MSAL library and application code.
Only identity-service HTTP responses and browser presentation were controlled
fixtures. A disposable Docker volume persisted state between containers and was
removed afterward. No existing user session, deployed listener or live token was
used. No image was pushed.

The packaged check is repeatable from the application root after building the
image, with Docker access:

```sh
python3 scripts/msal_image_checks.py --image confidential-ai-example:msal
```

Use `--docker 'sudo -n docker'` if that is the configured local access mechanism.
The exact-wheel lock was regenerated inside the pinned Python image. PyPI's
published vulnerability metadata listed no advisories for the nine newly added
exact dependency versions when checked; this is a limited metadata check.

## Implementation findings addressed

MSAL can remove expired access tokens while attempting a refresh. Persisting
those changes immediately altered the file even when renewal failed. The demo
now reloads under the Extensions lock, runs the operation against MSAL's
serializable cache, and atomically commits only on success. The same transaction
protects account removal and rejected interactive responses. Browser interaction
runs outside the lock.

Account selection after a new login requires matching MSAL account metadata to
that login's claims. An incomplete response cannot reuse a previous account just
because it is the only account in the cache. Local-logoff failure also exits with
a safe diagnostic instead of leaking nested errors or starting another login.

## Limits and next acceptance

Live Entra browser sign-in was explicitly deferred by the operator. Discovery
success does not establish app-registration callback acceptance, actual issued
API audience/scopes, live account metadata, or real refresh-token recovery.
Complete the live procedure in the root README before claiming those properties.

The cache is an explicitly unencrypted private file in the Docker volume. These
checks exercised normal container exits and controlled service failures. Abrupt
termination during locked I/O was not tested; a stale Extensions lock may require
operator cleanup after such a stop. Do not remove a lock held by a running client.

The request-boundary tests use controlled verifier/peer collaborators. This run
did not repeat live evidence collection, production HTTPS peer acceptance, Flint
inference, browser-extension acceptance, or cross-platform native installation.
Earlier attestation acceptance applies only to its own recorded revisions.

## Relevant source identities

| File | SHA-256 |
| --- | --- |
| `Dockerfile` | `edb5544d03f156799d629b8d16eaa64d1ccf716537e1c7bbebdba3294eb571fd` |
| `requirements.lock` | `d362e7043ac193263c8b252c63d9587541f59179c6ac3f5d687dd95f60fb582b` |
| `demo/identity.py` | `66fb3ee8c116a8a609d8521dfd95e643612d312327bb9d897cebc119e6466d3f` |
| `demo/identity_callback.py` | `d82e8e7951ff9fa1b937380a1a9cb73e10cd9ec5a0f9a08f49e7dcd5e156f2dc` |
| `confai-promter.py` | `171733bd5a998f6f88859e263564db5b7d360bbb79d710ebde0f427fa3f142b4` |
| `tests/test_identity.py` | `ff027a398d77111601bd60164e42c4509760da358416d34287e4392f8708a220` |
| `tests/test_identity_callback.py` | `39f8b53db0f34bcaac4aaa7b1739c1cc55fbd7c91a61179a62d3c7cb68340c74` |
| `tests/test_admission.py` | `4109174c38420a43bbf87ee430dfaa73e959d6aee063bfce5a33a7e328cb22fc` |
| `tests/identity_provider.py` | `ce65298bc0b4b3ba8d41b166f433cf4e272c6570ef5fa09c7555f16a5ba99ad9` |
| `tests/identity_image_probe.py` | `687628ec73f1719da557487e73624ea36f0d3a38eaa7cbff6273ac703594b368` |
| `scripts/msal_image_checks.py` | `d90b11404dc794c50f11308381c4bf1532142cdf44e1d724a050f253e80f454b` |
