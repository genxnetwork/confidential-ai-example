"""Point-in-time evidence appraisal before a cooperating client opens chat."""

import base64
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import openai

from demo import admission, collection
from demo.attestation_log import (
    color,
    describe_verification,
    format_utc,
)
from demo.attestation_log import (
    log as attestation_log,
)
from demo.runtime import ensure_runtime
from demo.transport import AppraisedTransport, SDK_PLACEHOLDER_API_KEY

POLICY_DIR = Path(
    os.environ.get("CONFIDO_POLICY_DIR", Path(__file__).with_name("profiles"))
)
ENDPOINTS = {
    "match": "match.demo.genxt.network",
    "mismatch": "mismatch.demo.genxt.network",
}


def load_policy(endpoint):
    return collection.load_policy(POLICY_DIR / f"{endpoint}.json")


def reference_link(policy):
    ref = policy["verifier"]["reference"]
    return f"https://github.com/{ref['repository']}/blob/{ref['commit']}/{ref['path']}"


def new_bundle_path(endpoint):
    root = Path(
        os.environ.get("CONFIDO_RUN_DIR", Path.home() / ".local/state/confido/runs")
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    run = root / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    )
    run.mkdir(mode=0o700)
    return run / f"{endpoint}.json"


def show_result(result, *, admitted=False, reason=None):
    print("\n" + color("ATTESTATION SUMMARY", "heading"))
    if result is None:
        print("  Evidence: NOT VERIFIED")
    else:
        kind = "ok" if result["status"] == "verified" else "error"
        print(
            f"  Evidence: {color(result['status'].upper(), kind)} ({result['reason']})"
        )
        print(
            f"  Confirmed IMA coverage: {result['coverage']['ima_entries']} entries; boot aggregate and kernel modules."
        )
    print(
        "  Application: "
        + color("ADMITTED" if admitted else "DENIED", "ok" if admitted else "error")
    )
    if reason:
        print("  Reason: " + str(reason))
    print(
        "Application/model files and GPU state are outside this measurement coverage."
    )


def setup_client(endpoint):
    """A current runtime and a fresh caller-owned run are required for admission."""
    runtime = ensure_runtime()
    policy = load_policy(endpoint)
    print("\nATTESTATION ENDPOINT | " + policy["origin"] + "/tee-report")
    print(color("Reference: " + reference_link(policy), "reference"))
    print(
        "A quote binds the challenge, certificate and IMA log. TLS session binding is unsupported."
    )
    answer = (
        input("Retrieve and verify the report before chat? [Y/n]: ").strip().lower()
    )
    if answer not in ("", "y", "yes"):
        print("Chat was not opened.")
        return None
    bundle_path = new_bundle_path(endpoint)
    result = None
    print(
        "\n"
        + color("ATTESTATION LOG", "heading")
        + "  "
        + format_utc(datetime.now(timezone.utc)),
        flush=True,
    )
    try:
        run = collection.collect_and_verify(policy, progress=attestation_log)
        result, archive = run.result, run.archive
        admission.save_private(bundle_path, archive)
        admission.save_private(
            bundle_path.with_suffix(".runtime.json"),
            {"runtime": runtime, "timings": run.timings},
        )
        describe_verification(
            result,
            base64.b64decode(archive["inputs"]["report"], validate=True),
            base64.b64decode(archive["inputs"]["reference"], validate=True),
        )
        attestation_log(f"Verification archive saved: {bundle_path}")
        if result["status"] != "verified":
            admission.save_private(
                bundle_path.with_suffix(".decision.json"),
                {
                    "schema_version": 2,
                    "application_admitted": False,
                    "reason": result["reason"],
                },
            )
            show_result(result, reason=result["reason"])
            print("Chat was not opened. No application request was sent.")
            return None
        attestation_log(
            "Authenticating the HTTPS peer against the quote-bound certificate"
        )
        session = admission.authenticate(policy, result, run=run)
        attestation_log("HTTPS peer and attestation endpoint authenticated")
        run.consume(policy, result)
        http_client = httpx.Client(
            transport=AppraisedTransport(session),
            follow_redirects=False,
            timeout=30.0,
        )
        # The SDK requires an API-key value; the scoped transport drops this
        # placeholder Authorization header before sending a request.
        client = openai.OpenAI(
            api_key=SDK_PLACEHOLDER_API_KEY,
            base_url=f"{policy['origin']}/v1",
            http_client=http_client,
            max_retries=0,
        )
    # Any collection, verification, transport, or client failure must deny admission.
    except Exception as error:  # noqa: BLE001
        admission.save_private(
            bundle_path.with_suffix(".decision.json"),
            {
                "schema_version": 2,
                "application_admitted": False,
                "reason": "collection_or_admission_failed",
                "detail": str(error),
            },
        )
        attestation_log(f"Application admission failed: {error}")
        show_result(result, reason=str(error))
        return None
    admission.save_private(
        bundle_path.with_suffix(".decision.json"),
        {
            "schema_version": 2,
            "application_admitted": True,
            "reason": "evidence_and_peer_verified",
            "origin": policy["origin"],
            "report_sha256": result["report_sha256"],
        },
    )
    show_result(result, admitted=True)
    print("Inference: Azure-hosted inference is outside the appraised VM.")
    return client


def chat_loop(client):
    """Run a chat session, then return to endpoint selection."""
    # Initialize conversation history
    conversation = [{"role": "system", "content": "You are a helpful assistant."}]

    print("\nWelcome to the Interactive Chat!")
    print("Type 'exit' or 'quit' to return to endpoint selection")
    print("Type 'clear' to start a new conversation")
    print("-" * 50)

    while True:
        # Get user input
        user_input = input("\nYou > ").strip()

        # Check for exit commands
        if user_input.lower() in ["exit", "quit"]:
            print("\nChat ended. Returning to endpoint selection.")
            return

        # Check for clear command
        if user_input.lower() == "clear":
            conversation = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
            print("\nConversation cleared!")
            continue

        if not user_input:
            continue

        # Add user message to conversation history
        conversation.append({"role": "user", "content": user_input})

        try:
            # Get completion from the model
            completion = client.chat.completions.create(
                model="llama-default", messages=conversation
            )

            # Extract and print the response
            assistant_response = completion.choices[0].message.content
            print("\nAssistant:", assistant_response)

            # Add assistant's response to conversation history
            conversation.append({"role": "assistant", "content": assistant_response})

        # Keep an admitted chat session usable after one failed API call.
        except Exception as e:  # noqa: BLE001
            print(f"\nError: {e!s}")
            print("Please try again.")


def main():
    print("\nConfido evidence-appraisal chat demo")
    print(
        "Before chat, Confido verifies TEE/HCL evidence, a challenge-bound vTPM quote, PCRs and the IMA log."
    )
    print()
    print(
        "TEE  = Trusted Execution Environment, isolating private VM memory "
        "from the hypervisor and providing CPU-signed attestation report."
    )
    print(
        "HCL  = Host Compatibility Layer, OpenHCL/OpenVMM paravisor whose "
        "attestation metadata binds the vTPM public key to the TEE report."
    )
    print(
        "TPM  = Trusted Platform Module (vTPM: virtual TPM); PCR = Platform Configuration Register"
    )
    print("IMA  = Integrity Measurement Architecture")
    while True:
        print("\n1. match.demo.genxt.network — expected reference match")
        print("2. mismatch.demo.genxt.network — expected reference mismatch")
        print("0. Exit")
        choice = input("\nEndpoint [1]: ").strip() or "1"
        if choice == "0":
            return
        endpoint = {"1": "match", "2": "mismatch"}.get(choice)
        if endpoint is None:
            print("Choose 0, 1 or 2.")
            continue
        try:
            client = setup_client(endpoint)
            if client is not None:
                try:
                    chat_loop(client)
                finally:
                    client.close()
        # Return to endpoint selection after any failed setup or session.
        except Exception as exc:  # noqa: BLE001
            print(f"\nRequest withheld: {exc}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
