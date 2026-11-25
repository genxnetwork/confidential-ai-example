# Container demo readiness — 2026-11-25 UTC

The current implementation is accepted locally as a development/staging demo.
Live Entra browser authentication and a complete authenticated Flint inference
session remain outstanding. This record does not authorize production use or
claim publication to GHCR.

## Artifact and source

- Branch: `revision/attestation-update`, starting HEAD `2391d09`.
- Upstream tracking state was refreshed with `git fetch origin`; the starting
  HEAD remained four commits ahead of its tracking branch.
- Local image: `confidential-ai-example:review-20261125`.
- Image ID: `sha256:e20321c877f9df7a9b4209f98a0f1d1fe9f70646f8b8ff8f76c2e9338a4529c9`.
- Platform: Linux amd64, CPython 3.15.2, verifier pipeline 2.
- SDK: `confido-client==0.2.1a1`, installed both in `.venv` and the image.
- Wheel SHA-256: `4e561dbb95b0df6a4ff6289fcf8da7df338cbb32d4255ee1f25da804ddf80520`.
- Upstream: `jandigitrust/confido`, successful main-branch push run `45709067114`,
  commit `2c2d4a47cd12d90300ea233950ecc4d556ea2bfa`.

The installer verified the downloaded archive against GitHub's SHA-256 before
loading the wheel and recorded its source after installation. Host and image
installation records identify the same wheel. These are source identities and
local acceptance evidence, not a signed build-provenance claim.

## Findings and checks

| Finding | Action and observed result |
| --- | --- |
| Native environment still had SDK 0.2.0 | Installed the compatible public alpha wheel; runtime compatibility and `pip check` pass. |
| Startup failure tests depended on installed SDK compatibility | Isolated runtime setup in the identity-failure cases, retaining real subprocess exit-code checks. |
| Image tests and publication rebuilt a moving upstream dependency | The final target now depends on its own successful test stage. CI builds and loads once, runs packaged checks, and retags/pushes that same image. |
| Unrecorded local acceptance | This record identifies the exact image, wheel, source inputs, completed checks and remaining acceptance. |

| Check | Result and limits |
| --- | --- |
| `make test` | All 46 tests passed with loopback sockets enabled. |
| Default Docker final build | Succeeded using the public upstream wheel; all 46 tests ran and passed inside its tests stage. |
| Deliberately failing test in a disposable build context | Building `final` failed. The check reused the tested image as runtime and the actual Dockerfile test/final stages; no project source was altered. |
| `pip check` in the final image | No broken requirements. |
| `python3 -m demo.runtime` in the final image with networking disabled | Compatible SDK/pipeline and matching installation provenance. |
| Packaged identity acceptance | All five phases passed: callback sign-in, outage preserving cache, renewal after restart, recovered-cache reuse and local logoff. Synthetic provider responses, real MSAL and disposable Docker state were used. |
| Public CIAM discovery in the final image | Succeeded with an empty temporary state filesystem and normal TLS validation. No user credentials were used. |
| Live public match endpoint, native SDK | Genoa `verified / reference_match`; HTTPS peer authenticated. |
| Live public mismatch endpoint, native SDK | Genoa `policy_mismatch / measurement_mismatch`. No admission or API request followed. |
| Workflow static review | No path filters or skipped test dependency; all referenced immutable action commits resolve. Hosted workflow execution and registry publication were not performed. |
| `git diff --check` | Passed. |

The live evidence checks used freshly prepared copies of the checked-in Genoa
policies. They sent neither a user token nor an inference request. Raw evidence,
identity cache contents and remote response bodies are not part of this record.
Launcher tests use a Docker CLI stub; they do not certify Docker Desktop on
Windows or macOS. The earlier [MSAL acceptance](msal-image-acceptance-20261125.md)
remains a separate record for its older SDK/image.

## Remaining live acceptance

On the Docker host, from this repository root, use a dedicated volume:

```sh
CONFIDO_IMAGE=confidential-ai-example:review-20261125 CONFIDO_STATE_VOLUME=confidential-ai-example-live-review ./run
```

Use the same command for each launch. The browser's `localhost:8765` must reach
that Docker host. For a remote host, forward port 8765 before opening the link.
Use the normal local mechanism for Docker daemon access.

1. Complete browser sign-in. Choose match, permit verification and send a
   synthetic prompt. Require admitted evidence/peer status and an actual chat
   response without exposing a token or printing private archives.
2. Return to endpoint selection and choose mismatch. Require denial with no
   chat request.
3. Exit normally, restart with the same volume and continue the saved identity.
   Require a working match chat without another interactive sign-in.
4. Repeat after the access token expires to exercise real silent renewal.
5. Restart, choose local logoff, then explicitly sign in again. Require a new
   browser flow and a working match chat.

Record only pass/fail, safe status categories, timestamp and image ID. Browser
sign-in, actual API audience/scope acceptance, real refresh-token recovery and
full inference remain unverified until these steps succeed. An operator must
perform the browser authentication; synthetic provider checks cannot replace it.

GHCR publication, anonymous pulls and hosted CI remain separate release checks.
Do not infer their success from the local image. Keep the reviewed local image
available while performing live acceptance; future upstream wheel selection
does not change the already-built image.

## Relevant source identities

The hashes below identify the inputs reviewed for this acceptance. Documentation
edits after the build do not enter the allowlisted Docker context. The Git commit
containing this record retains the maintained source; private state and candidate
wheels remain ignored.

| File | SHA-256 |
| --- | --- |
| `Dockerfile` | `0b53060a72bde67342d951c9aa4dcd7796878bac3713d2f3038c2083f4b7e83e` |
| `.dockerignore` | `21b886c66f2eaf32c05a2b4d8cc206e8ca6034dc2d36f88b36108368fddbad1f` |
| `.github/workflows/image.yml` | `ff2aff420d3f381dcc6ba92a593379e01d3c2c097c8d333e70abab5201c02eec` |
| `requirements.lock` | `d362e7043ac193263c8b252c63d9587541f59179c6ac3f5d687dd95f60fb582b` |
| `confido-client-wheel.json` | `f7d65581aa633c73de24287878482286371885256cefd5cdf79846f310c0ac57` |
| `confai-promter.py` | `171733bd5a998f6f88859e263564db5b7d360bbb79d710ebde0f427fa3f142b4` |
| `demo/admission.py` | `2308233b49c38ea5be50228e2967202d1754ab69a4bb937de2d62cf6b85a993d` |
| `demo/identity.py` | `66fb3ee8c116a8a609d8521dfd95e643612d312327bb9d897cebc119e6466d3f` |
| `demo/identity_callback.py` | `9b9cfabf69914d832f1b100114ba221d2e04bad2b482b690d06a0e4372b0fc3e` |
| `demo/runtime.py` | `7fde61dcc3664cc5022437bda8bb68a89aa5ce09c25fd487dd1a2d42a90124b4` |
| `demo/transport.py` | `c18c111665221cb7f5298c4a63dc7f367eb489f945f0e32901e76b36a4499ef1` |
| `scripts/install_client_wheel.py` | `eb938a8014ef87d6d3e09588eb9c02594ed4ad93a5c5fb08a921f150e5cbe600` |
| `scripts/download_client_wheel.py` | `de1d6d68286673d24c1bc271da0377b710268a2ca59b0a154d45fb3475f2fcb1` |
| `scripts/msal_image_checks.py` | `d90b11404dc794c50f11308381c4bf1532142cdf44e1d724a050f253e80f454b` |
| `tests/test_admission.py` | `e458036e3d5269b376f832a15d19e09a51e72b0ee134e5855ecd4f8bc47c4e89` |
| `profiles/verifier-genoa-stage-registry.json` | `7d3cf06255a691ecec351bfbeaa147317eb2de272a96969d437b051e8aceb3c1` |
| `profiles/verifier-genoa-stage-mismatch.json` | `394eef80e44b19c5c7a121b3335d0c6be80accf09285432d7930e226c1f8434d` |
