# Application JSON schemas

These JSON Schema Draft 2020-12 files describe records owned by the Confidential AI example. They are separate from [Confido's verifier contracts](https://github.com/jandigitrust/confido/tree/main/schemas).

| Schema | Purpose |
| --- | --- |
| [application-policy-v2.json](application-policy-v2.json) | Local HTTPS origin and verifier-policy selection for the application. The matching and mismatching examples are under [`profiles/`](../profiles/README.md). |
| [application-decision-v2.json](application-decision-v2.json) | Application admission outcome saved as `.decision.json` after evidence appraisal and the application's peer check. It is not a verifier result. |

Both records use `schema_version: 2`. The schemas document their serialized shape; the application code enforces the origin, credential timing, and transport checks at runtime.
