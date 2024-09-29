# Confidential AI Example

This repository contains a Dockerized application for a Confidential AI/LLM Service example. This app leverages Attested-TLS protocol, implemented by GENXT `confido` library, to verify and access Confidential LLM API service.

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

- `make promt`: This command runs the Docker container and executes the `confai-promter.py` Python script. You can pass arguments to the script by appending them to the `make promt` command.

- `make cli`: This command runs the Docker container in interactive mode with a bash shell, allowing you to manually run the `confai-promter.py` script.

## Example

```bash
make build
make promt write a haiku about recursion in programming
```

The `confido` library, configured by `confai-promter.py`, outputs debug messages during the verification of the Attested-TLS Evidence. This evidence includes the Trusted Platform Module (TPM) cryptographic report, as well as GPU and CPU Trusted Execution Environment (TEE) Remote Attestation reports. Notably, all these reports are cryptographically interconnected, and this interconnection is independently verified by the `confido` client library against CPU and GPU vendors' certificates and well-known software hash-sums.