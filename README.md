# Confidential AI Example

The client discovers `POST /tee-report` from `GET https://<host>/service-info`, sends a fresh nonce in JSON, verifies the returned certificate with Confido, and then opens the chat connection on the same HTTPS host. The service advertises `teeReport.sessionBinding.supported: false`: the report is nonce- and certificate-bound, but it is not cryptographically bound to the current TLS session. The console explains this limitation after showing the TRS link. The public `/aTLS` endpoint is no longer used. The console first displays service metadata as an unverified preview, shows the TEE report advertisement and configured TRS link, and prompts before report retrieval and appraisal (Enter accepts). Chat opens only after verification passes.

This repository contains a Dockerized client application for a Confidential AI/LLM Service example. This `confai-promter.py` app leverages the `Attested-TLS` protocol, implemented in the GENXT `confido` library. The confido library is a confdential computing middleware that serves as a specialised TLS certificate handler that, using a chain of cryptographically interlinked messages, verifies the authenticity and integrity of the entire software stack of the remote VM running the inference engine. It also independently verifies the CPU-signed evidence of the VM’s memory isolation. Within the Attested-TLS protocol, the CPU implementation is the only explicit trust anchor expected by the user.

The Docker image installs `confido-atls==0.2.0` from PyPI. This example has no
direct `azure-cvm-tooling` import; Confido 0.2.0 uses the pinned original
[Kinvolk azure-cvm-tooling repository](https://github.com/kinvolk/azure-cvm-tooling).
Build the image after Confido 0.2.0 has been published to PyPI.

## Local development

With `confido` and `confidential-ai-example` checked out side by side, run:

```bash
make dev-setup   # create .venv, install Python dependencies, build local Confido
make dev-chat    # run the example with the local Confido build
```

After changing Confido's Rust code, run `make dev-update` to rebuild and reinstall
its Python extension in `.venv`, then `make dev-chat` again. `make dev-info`
confirms that the installed extension came from your local Confido checkout
and shows its version. The virtual environment is ignored by Git. If the Confido checkout is
elsewhere, pass `CONFIDO_LIB=/path/to/confido/lib` to `make dev-update` (or
`make dev-setup`). Local development requires Python 3 with `venv` support (on Ubuntu, install
`python3-venv`), Rust, and the native Confido build dependencies described in
the sibling Confido README. `make dev-setup` installs maturin into `.venv`.

Use `make dev-update` followed by `make dev-chat` for this service-info
migration. The current `make build` / `make chat` Docker path still installs the
published `confido-atls==0.2.0` wheel, which calls the retired `/aTLS` endpoint.
It needs a new wheel release before that image can use `/service-info`.

## Requirements 

This example works on any platform and only requires [Docker](https://docs.docker.com/engine/install/) and `make` to be installed.

## Installing Make

### On Ubuntu/Debian

You can install `make` on Ubuntu or any other Debian-based system by running the following command in your terminal:

```bash
sudo apt-get install make
```

### On CentOS/RHEL

On CentOS, RHEL, or any other RedHat-based system, you can use the following command:

```bash
sudo yum install make
```

### On macOS

If you have Homebrew installed, you can install make by running:

```bash
brew install make
```

If you don't have Homebrew, you can install it by following the instructions on the [Homebrew](https://brew.sh/) website.

## Usage

You can run the following commands using `make`:

- `make build`: This command builds the Docker image with the tag `confidential-ai-example`. It creates a containerised environment with all the required dependencies, including the `confido` Attested-TLS library, the `httpx` standard HTTP client (which supports user-defined trusted TLS certificates), and the open-source [OpenAI](https://pypi.org/project/openai/) library for interacting with LLM inference engines.

- `make chat`: This command runs the Docker container and executes the `confai-promter.py` Python script. 

The `confido` library, configured by `confai-promter.py`, outputs debug messages during the verification of the Attested-TLS Evidence. After validating the SNP report and its HCL metadata binding, Confido extracts the vTPM attestation public key from that report metadata and uses it to verify the signed vTPM quote. This establishes the TEE-to-vTPM trust chain shown in the console. This evidence includes the Trusted Platform Module (TPM) cryptographic report, as well as GPU and CPU Trusted Execution Environment (TEE) Remote Attestation reports. Notably, all these reports are cryptographically interconnected, and this interconnection is independently verified by the `confido` client library against CPU and GPU vendors' certificates and well-known software hash-sums.

## Example 

For an example of the output generated by running the `make chat` command, refer to the [example-output.md](example-output.md) file.

