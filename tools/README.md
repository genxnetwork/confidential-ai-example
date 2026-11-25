# External operator and browser tooling

Reference enrollment lives in [`sanctio`](../../sanctio/README.md). The
application retains its issuer/platform decisions and selected policies.
See [the enrollment procedure](../docs/genoa-stage-reference.md).

Browser acceptance now belongs to Confido's `scripts/browser_live_checks.py`.
This application supplies `profiles/extension-origins.json` and the explicitly
Genoa-specific `profiles/browser-live-cases-genoa.json`. See
[the browser acceptance procedure](../docs/browser-acceptance.md).
