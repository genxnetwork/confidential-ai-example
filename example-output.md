# Revision demonstration output

The observed 2026-09-23 acceptance run used genuine VM SNP/HCL/vTPM evidence, the installed Confido 0.3.0 wheel and the frozen chat container. Its downstream OpenAI-compatible responder was **synthetic**; no inference verification is claimed. The public deployment is promoted separately.

The console retains the full ServiceInfo preview and detailed attestation logs. The following is an abbreviated stage summary; the retained run records in the sibling Confido revision artifacts are authoritative.

## Matching reference

```text
TEE attestation report is available (advertised; not yet verified).
TRS configured: <exact immutable reference URL from the verifier policy>
TLS session binding: NOT SUPPORTED.
Retrieve and appraise the report before chat? [Y/n]:

PASSED  endorsements
PASSED  snp_signature
PASSED  platform_policy
PASSED  hcl_key
PASSED  quote
PASSED  reference
PASSED  measurements
PASSED  https_peer

Decision: PASSED (reference_match)
IMA coverage: 47 enrolled entries; boot aggregate and kernel modules.
```

The vTPM public key comes from SNP-authenticated HCL metadata and verifies the quote. The quote binds the challenge, TLS certificate and IMA log. The intended HTTPS hostname and critical metadata are checked before application credentials are read.

## Incompatible reference

```text
PASSED  endorsements
PASSED  snp_signature
PASSED  platform_policy
PASSED  hcl_key
PASSED  quote
PASSED  reference
FAILED  measurements

Decision: POLICY_MISMATCH (measurement_mismatch)
Chat was not opened. No application request or credential was sent.
```

Both installed-wheel and container cases admitted one synthetic request for match and emitted zero application requests for mismatch. Other-origin requests, a wrong TLS hostname and changed service identity were rejected. Discovery/report requests carried no application credentials.

For the configured public demo, `llama-default` forwards to Azure-hosted inference outside the appraised VM. TLS session binding, continuous/server-side capability enforcement and application/model/GPU measurement remain outside this revision's assurance claims.
