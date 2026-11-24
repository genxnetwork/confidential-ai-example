# Agent guidance

This repository is the Confidential AI example using the Confido 0.2 verifier.
Start with `README.md`. For Genoa reference enrollment, read
`docs/genoa-stage-reference.md` and `profiles/README.md` before the relevant
policy files.

- `demo/` owns report retrieval and application admission; `native_transport/`
  authenticates the TLS peer. `schemas/` documents application-owned records;
  `profiles/` contains local demo decisions and
  verifier policy pins; `scripts/enroll_reference.py` checks a published
  registry entry before generating a policy.
- The sibling `confido` repository owns evidence verification; `attestor` owns
  native collection and the direct report endpoint. This application does not
  publish reference values.
  Keep stage candidates and their limited measurement coverage clearly labeled.

## Context and private data

- Scope searches to relevant source, profiles, tests, and documentation. Exclude
  `build/`, `native_transport/target/`, `.venv/`, `.artifacts/`, caches, and
  logs from broad searches.
- Build and test tools may use generated files locally. Do not print, attach,
  or paste caches, binaries, credentials, private keys, or raw live run archives
  into model context, issues, or PRs. For diagnosis, report only necessary
  metadata, counts, hashes, or redacted fields.
- `.gitignore` limits accidental Git staging; it does not control what an
  agent reads or sends to a model. Check tool output before exposing it.

## Verification

Run `make test` for application changes, with narrower checks while iterating.
Before handing off, check `git status --short` and `git diff --check`; keep test
output free of credentials and raw evidence.
