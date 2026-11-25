# Third-party material

The root LICENSE applies to this example's project-authored material. Dependencies
retain their own terms; the project's Apache-2.0 licence does not replace them.

This example installs the pinned JAN Confido `confido-client` wheel. Its native
dependencies and notices belong to that wheel's distribution. The example does
not build or distribute its own Rust transport. The Python dependency set is
pinned in `requirements.lock`; installed distributions retain their own licence
metadata. Review the final wheel and container inventories before public
distribution.

MSAL Python and MSAL Extensions are MIT-licensed. Their runtime dependencies,
including requests, PyJWT and cryptography, retain their own installed licence
metadata. The image installs the exact wheels in `requirements.lock`; no
platform keychain or broker extra is included.

These notices document upstream terms; they do not establish ownership or
licence compatibility.
