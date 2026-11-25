# One container image for user execution

The chosen user prerequisite is Docker with Linux containers. Linux/macOS `run`
and Windows `run.cmd` / `run.ps1` only pull and run the same `linux/amd64` image.
There is no host Python installer, environment migration or native Windows ACL
implementation to maintain in this example. Docker Desktop supplies the Linux
VM and, on Apple Silicon, CPU emulation. Confido's reusable native macOS wheels
remain a separate library capability.

## User state and authentication

The wrapper publishes only host loopback port 8765 for the browser callback.
The listener binds to the container's interfaces; the user opens its sign-in link
in a browser on the host. A named volume retains the session and run archives
under `/state/confidential-ai-example/`. Linux filesystem permissions protect
those files consistently regardless of host OS. Updating/recreating the container
does not remove that volume. Old native sessions and existing Docker volumes are
not deleted or silently migrated.

## Build versus launch

CI selects the latest successful Confido main-branch client wheel inside the
Linux image build, validates GitHub's archive checksum and records wheel/run/commit
metadata after installation. Builds can explicitly select an unpublished Linux
candidate. The final image depends on a successful test stage of the same runtime.
CI builds and loads that image once, checks packaged identity across container
restarts, and retags and pushes the checked image without rebuilding. Failed
checks prevent publication; user startup does not
invoke pip, build an image, hash source files or require a retained wheel.
The private build context excludes local environments and archives.

At runtime, the application checks only the public APIs, supported version and
verifier pipeline. Admission, policy pins and live peer authentication remain
application decisions. Local installation records are diagnostic information,
not an attestation of the application.

The package locks now target exactly one Python/platform combination, with one
verified SHA-256 per selected wheel. Enrollment and its Python cryptography dependency have moved to the separate
`../sanctio/` project. The application image does not install them.

## Distribution and validation boundary

The image workflow publishes GHCR tags for pushed branches/commits and `latest`
on the default branch. The first package publication must be made public for
anonymous user pulls. Local source changes and local smoke images are not a
published release. The [dated readiness record](release-readiness-20261125.md)
identifies the available upstream Python 3.15 wheel and local acceptance.

Launch-wrapper tests exercise image reuse, state/callback mapping, quoting and
Docker failures. PowerShell can be tested on Linux and has a native Windows CI
job. These checks do not certify unperformed Docker Desktop/browser acceptance
on Windows or macOS; live matching and mismatching attestation must be checked
on those hosts before claiming that acceptance.
