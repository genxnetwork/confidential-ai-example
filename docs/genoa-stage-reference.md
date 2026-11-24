# Genoa stage reference enrollment

Genoa is the AMD EPYC processor generation used by the current local test VM.
Here, a stage reference means a candidate enrollment for that test environment.

The Teraveri registry holds the immutable Genoa 1071 stage reference. GENXT's
one-use Ed25519 publisher statement is copied into that registry entry. This
application chooses which issuer and platform it trusts through
`profiles/reference-issuers-stage.json` and `profiles/platform-genoa-stage.json`.
The verifier consumes the resulting policy bytes; registry content cannot add
trusted issuers on its own.

The stage candidate covers boot aggregate and kernel module IMA events. It does
not claim to measure application, model or GPU state. The positive policy pins
Teraveri commit `3fa7913d44a377806bd94126589be1feb362b6cb`; the negative
policy pins an unendorsed test fixture at commit
`8462ca8808d85395397d847fae6446d380a1320c`. That fixture changes the
`filedata_hash` of two Genoa kernel modules and keeps the same platform
enrollment. The first live acceptance is in
`../../confido/docs/revision/acceptance-genoa-manual-20261123.md`.
The later direct report endpoint acceptance is in
`../../confido/docs/revision/acceptance-genoa-direct-20261123.md`. It passed on
isolated local ports with a synthetic downstream responder, including a
rebuilt local container match/mismatch run. Public deployment still requires
its own configuration review and promotion.

To regenerate the positive policy from a clean checkout at the pinned registry
commit:

```sh
python3 scripts/enroll_reference.py \
  --registry teraveri/reference-value-registry \
  --commit 3fa7913d44a377806bd94126589be1feb362b6cb \
  --entry entries/azure-snp-vtpm-ima-1/azure-genoa-ubuntu2204-kernel-1071-stage \
  --issuer GENXT-manual \
  --registry-dir ../reference-value-registry \
  --output profiles/verifier-genoa-stage-registry.json
```

The GENXT Actions OIDC publisher path is still blocked by its required CI job;
the current stage uses only the key and manifest explicitly pinned to
`GENXT-manual`. Do not treat the presence of the unused `GENXT` issuer entry as
a successful OIDC publication. If that workflow becomes available, verify its
bundle, update this application's issuer decision and rerun the acceptance.

The [Attestor deployment guide](https://github.com/jandigitrust/attestor/blob/main/deploy/README.md)
explains how its operator starts an isolated collector on `127.0.0.1:18001`
with a certificate for `localhost`. For positive/negative hardware acceptance,
use [Attestor's optional integration harness](https://github.com/jandigitrust/attestor/blob/main/integration/README.md)
with this client's pinned policies. The harness manages a temporary HTTPS
frontend and synthetic downstream responder on isolated local ports; it does
not manage Attestor or evaluate external inference.
