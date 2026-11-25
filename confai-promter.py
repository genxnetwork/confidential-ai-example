"""Sign in once and admit chat only after live evidence and HTTPS peer checks.

Confido owns evidence appraisal and peer authentication. This application owns
policy selection, the user session, allowed chat routes, and admission records.
"""

import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import openai

from demo import admission, identity, policy as app_policy
try:
    import confido_client
    from confido_client.httpx_transport import ScopedTransport
    from confido_client.console import color, print_verification, format_utc
    from confido_client.console import log as attestation_log
except ImportError:
    raise SystemExit("Confido client API is missing. Run ./run --update (Windows: .\\run.cmd --update).") from None
from demo.runtime import ensure_runtime
from demo.transport import ChatTransport

POLICY_DIR = Path(
    os.environ.get("CONFIDO_POLICY_DIR", Path(__file__).with_name("profiles"))
)
CHAT_MODEL = "tinyllama-1.1b-chat-v1.0"
CHAT_MAX_TOKENS = 16
SYSTEM_PROMPT = "You are a helpful assistant. Answer in one short sentence."


def safe_error_message(error):
    """Describe failure without displaying remote bodies, tokens, or cause chains."""
    if isinstance(error, identity.SessionUnavailable):
        return "Sign-in service is unavailable. Saved session kept; try again later."
    if isinstance(error, (openai.APIStatusError, httpx.HTTPStatusError)):
        if isinstance(error, openai.APIStatusError):
            status = error.status_code
        else:
            status = error.response.status_code
        return f"Request failed (HTTP {status})."
    if isinstance(error, (openai.APITimeoutError, httpx.TimeoutException)):
        return "Request timed out. The remote outcome may be unknown."
    if isinstance(error, (openai.APIConnectionError, httpx.TransportError)):
        return "Connection failed or timed out. The remote outcome may be unknown."
    return f"Operation failed ({type(error).__name__})."


def load_policy(endpoint):
    return app_policy.load_policy(POLICY_DIR / f"{endpoint}.json")


def reference_link(policy):
    ref = policy["verifier"]["reference"]
    return f"https://github.com/{ref['repository']}/blob/{ref['commit']}/{ref['path']}"


def new_bundle_path(endpoint):
    """Create a private directory for one appraisal and its admission records."""
    state_root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    default_runs = state_root / "confidential-ai-example/runs"
    root = Path(os.environ.get("CONFIDO_RUN_DIR", default_runs))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    run = root / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    )
    run.mkdir(mode=0o700)
    return run / f"{endpoint}.json"


def show_result(result, *, admitted=False, reason=None):
    """Present evidence status separately from the application's admission decision."""
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


def collect_attempt(policy):
    """Return a fresh live appraisal and its duration; this does not admit chat."""
    print(
        "\n"
        + color("ATTESTATION LOG", "heading")
        + "  "
        + format_utc(datetime.now(timezone.utc)),
        flush=True,
    )
    attestation_log("Requesting fresh challenge-bound evidence and appraising it locally")
    started = time.monotonic()
    attempt = confido_client.appraise(
        policy["origin"],
        policy["verifier_bytes"],
        policy.get("allow_untrusted_bootstrap", False),
    )
    appraisal_ms = (time.monotonic() - started) * 1000
    attestation_log(f"Evidence collected and appraised in {appraisal_ms:.1f} ms")
    return attempt, appraisal_ms


def record_attempt(attempt, bundle_path, runtime, appraisal_ms):
    """Save private evidence and runtime records, then render the verifier checks."""
    admission.save_private(bundle_path, attempt.archive)
    admission.save_private(
        bundle_path.with_suffix(".runtime.json"),
        {"runtime": runtime, "timings": {"appraisal_ms": appraisal_ms}},
    )
    print_verification(attempt)
    attestation_log(f"Verification archive saved: {bundle_path}")


def create_chat_client(session, auth, origin):
    """Use the peer-checked transport and resolve the current token per request."""
    http_client = httpx.Client(
        transport=ChatTransport(ScopedTransport(session), lambda: auth.access_token),
        follow_redirects=False,
        timeout=30.0,
        trust_env=False,
    )
    return openai.OpenAI(
        api_key=auth.token,
        base_url=f"{origin}/v1",
        http_client=http_client,
        max_retries=0,
    )


def setup_client(endpoint, auth, *, runtime=None):
    """Collect and authenticate one live attempt before constructing a chat client.

    Decline or failure withholds chat. Archive and decision records are private
    diagnostics, separate from the live context consumed by peer authentication.
    """
    if runtime is None:
        runtime = ensure_runtime()
    policy = load_policy(endpoint)
    print("\nATTESTATION ENDPOINT | " + policy["origin"] + "/tee-report")
    print(color("Reference: " + reference_link(policy), "reference"))
    print(
        "A quote binds the challenge, certificate and IMA log. TLS session binding is unsupported."
    )
    answer = input("Retrieve and verify the report before chat? [Y/n]: ").strip().lower()
    if answer not in ("", "y", "yes"):
        print("Chat was not opened.")
        return None

    bundle_path = new_bundle_path(endpoint)
    result = None
    try:
        attempt, appraisal_ms = collect_attempt(policy)
        result = attempt.result
        record_attempt(attempt, bundle_path, runtime, appraisal_ms)
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
        session = admission.authenticate(policy, result, attempt=attempt)
        attestation_log("HTTPS peer and attestation endpoint authenticated")
        client = create_chat_client(session, auth, policy["origin"])
    # Any collection, verification, transport, or client failure must deny admission.
    except Exception as error:  # noqa: BLE001
        detail = safe_error_message(error)
        admission.save_private(
            bundle_path.with_suffix(".decision.json"),
            {
                "schema_version": 2,
                "application_admitted": False,
                "reason": "collection_or_admission_failed",
                "detail": detail,
            },
        )
        attestation_log("Application admission failed: " + detail)
        show_result(result, reason=detail)
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
    print(
        "Inference: TinyLlama runs on the TEE VM; its model and runtime are "
        "outside the measured IMA reference."
    )
    return client


def chat_loop(client):
    """Run a chat session, then return to endpoint selection."""
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("\nWelcome to the Interactive Chat!")
    print("Type 'exit' or 'quit' to return to endpoint selection")
    print("Type 'clear' to start a new conversation")
    print("-" * 50)

    while True:
        user_input = input("\nYou > ").strip()

        if user_input.lower() in ("exit", "quit"):
            print("\nChat ended. Returning to endpoint selection.")
            return

        if user_input.lower() == "clear":
            conversation = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
            print("\nConversation cleared!")
            continue

        if not user_input:
            continue

        conversation.append({"role": "user", "content": user_input})

        try:
            print("\nGenerating a short response...", flush=True)
            completion = client.chat.completions.create(
                model=CHAT_MODEL, messages=conversation, max_tokens=CHAT_MAX_TOKENS
            )

            assistant_response = completion.choices[0].message.content
            print("\nAssistant:", assistant_response)
            if completion.choices[0].finish_reason == "length":
                print("Reply reached this CPU demo's short-response limit.")

            conversation.append({"role": "assistant", "content": assistant_response})

        except openai.AuthenticationError:
            print("\nAPI rejected the access token (HTTP 401). Saved sign-in kept. "
                  "Check the API's token validation and access configuration.")
            return
        except identity.AuthenticationRequired:
            raise
        # Keep an admitted chat session usable after one failed API call.
        except Exception as error:  # noqa: BLE001
            print("\n" + safe_error_message(error))


def show_intro():
    """Explain the attestation terms and coverage before endpoint selection."""
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


def choose_endpoint():
    """Return a selected local policy name, or None when the user exits."""
    while True:
        print("\n1. match.demo.genxt.network — expected reference match")
        print("2. mismatch.demo.genxt.network — expected reference mismatch")
        print("0. Exit")
        choice = input("\nEndpoint [1]: ").strip() or "1"
        if choice == "0":
            return None
        endpoint = {"1": "match", "2": "mismatch"}.get(choice)
        if endpoint is None:
            print("Choose 0, 1 or 2.")
            continue
        return endpoint


def main():
    """Check the runtime, sign in once, and reuse the session across endpoints."""
    print("\nConfido evidence-appraisal chat demo")
    try:
        runtime = ensure_runtime()
    except RuntimeError:
        print("Client runtime is incompatible. Run ./run --update (Windows: .\\run.cmd --update).", file=sys.stderr)
        return 1
    try:
        auth = identity.authenticate()
    except Exception as error:
        print("Email sign-in failed. " + safe_error_message(error), file=sys.stderr)
        return 1
    if auth is None:
        return 0

    show_intro()
    while True:
        endpoint = choose_endpoint()
        if endpoint is None:
            return 0
        try:
            client = setup_client(endpoint, auth, runtime=runtime)
            if client is not None:
                try:
                    chat_loop(client)
                finally:
                    client.close()
        except identity.AuthenticationRequired:
            print("Sign-in expired or was rejected. Please sign in again.")
            try:
                identity.logoff(auth)
                auth = identity.authenticate()
            except Exception as error:
                print("Email sign-in failed. " + safe_error_message(error), file=sys.stderr)
                return 1
            if auth is None:
                return
        # Return to endpoint selection after any failed setup or session.
        except Exception as exc:  # noqa: BLE001
            print("\nRequest withheld: " + safe_error_message(exc))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
