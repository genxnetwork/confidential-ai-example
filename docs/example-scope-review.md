# Example scope and extraction review

The product is a small cooperating client: select a local policy, appraise live
attestation with Confido, authenticate the HTTPS peer, then call an
OpenAI-compatible LLM service. The current sign-in and Docker launch contract
remains supported. This review does not attest the LLM, model, or application.

## Ownership decisions

Teraveri registry consumers authenticate publisher statements using consumer-owned
trust decisions. A registry consumer CLI is the appropriate destination for the
reusable enrollment mechanism. Publishing a manifest and deciding to trust it
remain separate responsibilities. No cross-repository migration is claimed here.

Confido owns generic evidence/peer checks and their rendering. The example owns
admission, API routes, identity selection, and policies. OAuth is reusable in
principle, but provider-specific credentials and scopes do not belong in the
portable verifier. Extract it only with an actual identity-tool consumer contract.

Tests remain at the boundary they protect. Keep negative no-request cases,
credential redaction, session renewal failure/rotation, real callback sockets,
artifact corruption, CLI exit status, and launcher quoting. Do not replace these
with mocks of the operation under test or add tests just for extracted helpers.

## File decisions

This inventory excludes generated environments, archives, caches and deleted
files. Historical output is classified without treating it as validation.
Line counts describe the inspected working copy, before this report was added.

| File | Lines | Decision |
| --- | ---: | --- |
| `.dockerignore` | 33 | Retain; supporting project or distribution configuration. |
| `.gitattributes` | 3 | Retain; supporting project or distribution configuration. |
| `.github/workflows/image.yml` | 58 | Retain; supporting project or distribution configuration. |
| `.gitignore` | 187 | Large inherited template. Preserve protections against existing private/generated files; pruning requires checking newly exposed paths, not just removing unused framework names. |
| `.python-version` | 1 | Retain; supporting project or distribution configuration. |
| `AGENTS.md` | 38 | Removed; shared rules and repository navigation now live at the workspace root. |
| `CLAUDE.md` | 1 | Removed; the workspace root supplies the shared entry point. |
| `Dockerfile` | 32 | Retain single Linux target. Follow-up: COPY . still ships tests and enrollment tool; use explicit runtime inputs before extracting tooling dependencies. |
| `LICENSE` | 201 | Retain; supporting project or distribution configuration. |
| `Makefile` | 12 | Retain; supporting project or distribution configuration. |
| `README.md` | 202 | Shortened to launch, identity/admission contract and developer checks; detailed trust flow moved to docs/attestation-flow.md. |
| `THIRD_PARTY_NOTICES.md` | 14 | Retain; supporting project or distribution configuration. |
| `confai-promter.py` | 352 | Retain the visible sign-in -> appraisal -> peer check -> OpenAI request sequence. Removed unused endpoint constants. |
| `confido-client-wheel.json` | 12 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `demo/README.md` | 21 | Retain; supporting project or distribution configuration. |
| `demo/__init__.py` | 1 | Retain; functions have a focused scope. |
| `demo/admission.py` | 32 | Retain application-owned origin/policy binding and decision boundary. save_private is small; a generic storage package is unjustified. |
| `demo/identity.py` | 337 | Deployment-specific OAuth and persistence dominate example size. Candidate for Teraveri identity tooling, not Confido evidence verification. |
| `demo/policy.py` | 59 | Retain bounded local policy selection; Genoa preparation is deployment setup, not verifier logic. |
| `demo/runtime.py` | 73 | Retain compact compatibility check; avoid restoring source manifests and auto-installation. |
| `demo/transport.py` | 29 | Retain route and credential constraints here; origin/TLS verification already belongs to Confido. |
| `docs/genoa-stage-reference.md` | 56 | Retain deployment-specific enrollment provenance and updated operator-tool invocation. |
| `docs/runtime-and-wheel-review.md` | 50 | Architecture decision context; not a second launch procedure. |
| `example-output.md` | 105 | Historical console output; not revalidated as current evidence or read as live input. Label with source revision before reuse. |
| `profiles/README.md` | 44 | Retain; supporting project or distribution configuration. |
| `profiles/extension-origins.json` | 6 | Browser-specific deployment fixture; move with extension acceptance when its consumer interface is ready. |
| `profiles/match.json` | 6 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `profiles/mismatch.json` | 6 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `profiles/platform-genoa-stage.json` | 6 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `profiles/reference-issuers-stage.json` | 30 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `profiles/verifier-genoa-stage-mismatch.json` | 16 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `profiles/verifier-genoa-stage-registry.json` | 21 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `profiles/verifier-match.json` | 21 | Legacy Milan fixture used by native tests/tools; do not remove until those consumers explicitly select Genoa. |
| `profiles/verifier-mismatch.json` | 21 | Legacy negative Milan fixture; preserve paired semantics until native consumers migrate. |
| `requirements-tooling.in` | 2 | Enrollment-only cryptography; keep separate until operator tests migrate to the supported Teraveri tool. |
| `requirements-tooling.lock` | 6 | Retain runtime/tooling split and target-specific hashes; document regeneration. |
| `requirements.in` | 2 | Retain runtime/tooling split and target-specific hashes; document regeneration. |
| `requirements.lock` | 20 | Retain runtime/tooling split and target-specific hashes; document regeneration. |
| `ruff.toml` | 2 | Updated stale py310 target to py315; no new linter dependency introduced. |
| `run` | 46 | Retain; supporting project or distribution configuration. |
| `run.cmd` | 3 | Retain; supporting project or distribution configuration. |
| `run.ps1` | 51 | Retain; supporting project or distribution configuration. |
| `schemas/README.md` | 10 | Retain; supporting project or distribution configuration. |
| `schemas/application-decision-v2.json` | 36 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `schemas/application-policy-v2.json` | 34 | Retain explicit local policy/schema; do not infer trust from registry contents. |
| `scripts/README.md` | 17 | Retain; supporting project or distribution configuration. |
| `scripts/download_client_wheel.py` | 111 | Retain; functions have a focused scope. |
| `scripts/install_client_wheel.py` | 125 | Retain; functions have a focused scope. |
| `scripts/live_acceptance.py` | 28 | Retain isolated end-to-end admission check; synthetic response expectation limits it to staging, not arbitrary LLM services. |
| `scripts/preflight.py` | 43 | Small optional live peer diagnostic; offline mode overlaps run --info, but online mode has a distinct no-inference purpose. |
| `tests/README.md` | 24 | Retain; supporting project or distribution configuration. |
| `tests/enrollment/test_enroll_reference.py` | 292 | Keep publisher/claim/key/digest negative cases with operator tooling; migrate together with its eventual Teraveri interface. |
| `tests/test_admission.py` | 255 | Retain admission order, forbidden-effect assertions, real SDK transport, redaction and process exit tests. Confido internals stay mocked at this application boundary. |
| `tests/test_client_wheel.py` | 72 | Retain wrong-distribution/native-module rejection and provenance-after-install checks. |
| `tests/test_download_client_wheel.py` | 66 | Retain build-selection and corruption-before-extraction checks; avoid asserting helper structure. |
| `tests/test_identity.py` | 208 | Retain session permissions/rotation, temporary-failure retention and real callback sockets. Removed duplicate mock-only revocation test. |
| `tests/test_identity_transport.py` | 43 | Retain route/token rejection before forwarding; this does not claim to verify native TLS. |
| `tests/test_policy.py` | 46 | Retain local path/origin containment and bounded loading contract. |
| `tests/test_run.py` | 107 | Retain Docker CLI stub coverage for quoting, state, platform, update and exit propagation; not Docker Desktop acceptance. |
| `tests/test_runtime.py` | 52 | Retain installed API/pipeline compatibility and regression against requiring source/build manifests. |
| `tools/README.md` | 22 | Retain; supporting project or distribution configuration. |
| `tools/browser_live_checks.py` | 64 | Isolated from application helpers. Candidate for Confido extension integration fixtures; not a chat dependency. |
| `tools/enroll_reference.py` | 477 | Isolated from build helpers. Extract generic consumer verification to Teraveri; retain local issuer/platform choices here. |

`docs/attestation-flow.md` retains the detailed trust and deployment explanation extracted from the quickstart. `tools/README.md` defines operator-tool ownership and migration boundaries.

The mocked `Session.token` revocation test was removed: the explicit OAuth `invalid_grant` test exercises the same recovery through the real renewal code and checks a fresh login. Callback concurrency and transient-error tests remain distinct.

## Enrollment extraction update

Enrollment implementation, ten tests, and cryptography dependency inputs moved
to `/mnt/sanctio` without Git initialization. Public fixture
copies make its tests independent of the application. The CLI now requires
explicit issuer, issuer policy, and platform inputs. The application retains
its local decisions and generated verifier policies. Earlier inventory rows
record the pre-extraction state; removed paths are historical, not instructions.
