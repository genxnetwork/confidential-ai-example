# Opt-in Genoa browser acceptance

Confido owns the browser runner and extension implementation. This example owns
the approved origin list, Genoa policies, and expected positive/negative cases.
The application does not depend on Playwright to run or test its chat flow.

The migrated runner is available on JAN Confido `main` through
[PR #8](https://github.com/jandigitrust/confido/pull/8). Use a Confido checkout
containing that merge; a separate browser-check worktree is not required.

Prepare the browser build tools and Playwright/Chromium as described in Confido's
`extension/README.md`. From the selected Confido worktree root:

```sh
python3 extension/build.py --browser chromium --origins-config ../confidential-ai-example/profiles/extension-origins.json
python scripts/browser_live_checks.py \
  --extension-dir extension/dist/chromium \
  --cases ../confidential-ai-example/profiles/browser-live-cases-genoa.json \
  --pregrant-hosts
```

The public services must actually use the Genoa stage enrollment represented
by these policies. This procedure does not establish their current deployment
state. For another environment, supply an explicitly approved case file; do not
weaken a policy or fall back to a different reference to obtain a passing result.

Each case must produce the expected evidence status and reason without an
application-admission claim. A failure returns nonzero; no chat or user access
token is involved. Native pinned-peer admission remains a separate application
check. Browser TLS must succeed without certificate-error bypasses.

`--pregrant-hosts` changes only a temporary copy of the package. It exercises
live collection with already granted permissions and does not validate the
actual browser permission dialog, denial, or revocation. Full live hardware
acceptance and production consent-flow acceptance are separate from offline
tests of the runner. For operator-driven consent, omit `--pregrant-hosts` and
use `--headed` on a desktop with a display server.
