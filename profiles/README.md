# Demo policies and Genoa stage enrollment

Genoa and Milan are AMD EPYC processor generations. The current local test VM
uses Genoa; the original demo profiles target Milan. Each needs the matching
AMD certificate chain and its own enrolled platform and measurement values.

This directory contains **application-selected** policies. Confido verifies
evidence against policy bytes supplied by its caller; it does not select an
origin, issuer, platform enrollment, or reference from network responses.
This repository defines its [application policy and decision schemas](../schemas/README.md).
Confido's verifier JSON contracts are in `../confido/schemas/` when the two
repositories are checked out side by side.

| Files | Purpose |
| --- | --- |
| [browser-live-cases-genoa.json](browser-live-cases-genoa.json) | Opt-in Genoa browser acceptance cases for the Confido runner; selects exact policy files and expected evidence status/reason. |
| [extension-origins.json](extension-origins.json) | Client-side browser extension origin allowlist for the demo; it is not a server routing configuration. |
| [match.json](match.json), [mismatch.json](mismatch.json) | Application policies: HTTPS origin, verifier-policy filename, and explicit untrusted bootstrap option. The Genoa console command copies these and selects different verifier files. |
| [verifier-match.json](verifier-match.json), [verifier-mismatch.json](verifier-mismatch.json) | Matching and deliberately incompatible Milan reference pins for those two application policies. |
| [platform-genoa-stage.json](platform-genoa-stage.json) | Observed Genoa stage platform enrollment used when generating a verifier policy. It is not a vendor certification. |
| [reference-issuers-stage.json](reference-issuers-stage.json) | Local issuer decision for the Teraveri stage manifest. The current accepted `GENXT-manual` key and manifest are pinned here; the `GENXT` Actions/OIDC entry is a future path, not a completed endorsement. |
| [verifier-genoa-stage-registry.json](verifier-genoa-stage-registry.json) | Positive Genoa stage policy generated from a publisher-authenticated stage candidate at a full commit and content digest; this is not an independently approved production baseline. |
| [verifier-genoa-stage-mismatch.json](verifier-genoa-stage-mismatch.json) | Negative Genoa stage policy with the same platform constraints and a pinned Teraveri test fixture whose `nf_tables.ko` and `bridge.ko` file digests differ. The fixture is not an endorsed enrollment. |

The Milan pair and Genoa stage pair are distinct enrollments. A file named
`match` means it is intended to match its enrolled reference, not that any
future host or workload is approved. The stage reference covers a boot
aggregate and enrolled kernel modules; it does not cover application code,
models, GPU state, or inference output.

The Genoa mismatch fixture keeps the positive reference's entry count, order,
boot aggregate, template hashes and PCR 10 value. Only two module file digests
change, so the negative run exercises the IMA comparison instead of a platform
or reference-format failure.

The application policy uses schema version **2** and points to a verifier
policy with schema version **2**. Both use evidence profile
`azure-snp-vtpm-ima/1`. The Python SDK version is selected explicitly by
[`confido-client-wheel.json`](../confido-client-wheel.json); its native components
use SemVer prerelease spelling while Python uses PEP 440. Runtime compatibility
also requires verifier pipeline revision 2. Wire and schema versions remain
separate contracts.

See [Genoa stage enrollment](../docs/genoa-stage-reference.md) for the pinned
registry commit, enrollment command, and isolated match/mismatch run. A new
image, kernel, or issuer approval requires a reviewed policy update and fresh
acceptance; editing a reference to force a pass is not an approval process.
