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

To regenerate the positive policy using the public registry at the pinned
commit, first prepare the separate
[reference client environment](../../sanctio/README.md).
From this example's root in a Unix shell, without a local registry checkout:

```sh
../sanctio/.venv/bin/python ../sanctio/enroll_reference.py \
  --issuer-policy profiles/reference-issuers-stage.json \
  --platform profiles/platform-genoa-stage.json \
  --registry teraveri/reference-value-registry \
  --commit 3fa7913d44a377806bd94126589be1feb362b6cb \
  --entry entries/azure-snp-vtpm-ima-1/azure-genoa-ubuntu2204-kernel-1071-stage \
  --issuer GENXT-manual \
  --output profiles/verifier-genoa-stage-registry.json
```

For offline enrollment, `--registry-dir ../reference-value-registry` is also
supported when that checkout is clean and checked out at the exact pinned
commit. This command verifies the publisher statement once; live runs fetch
the pinned `reference.json` and verify its digest, but do not repeat publisher
authentication.

The current stage pin uses only the key and manifest explicitly approved under
`GENXT-manual`. The separate `GENXT` Actions/OIDC issuer entry does not endorse
this manifest. Using an Actions publication requires verifying its bundle,
updating this application's issuer decision and rerunning acceptance.

The [Attestor deployment guide](https://github.com/jandigitrust/attestor/blob/main/deploy/README.md)
explains how its operator starts an isolated collector on `127.0.0.1:18001`
with a certificate for `localhost`. For positive/negative hardware acceptance,
use [Attestor's optional integration harness](https://github.com/jandigitrust/attestor/blob/main/integration/README.md)
with this client's pinned policies. The harness manages a temporary HTTPS
frontend and synthetic downstream responder on isolated local ports; it does
not manage Attestor or evaluate model integrity or inference output.
