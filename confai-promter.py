import confido
import os
from pathlib import Path
import json
import httpx
import ssl
import openai

TRS_REGISTRY = "genxnetwork/confido-trusted-repository"
TRS_SOURCE = f"https://github.com/{TRS_REGISTRY}"

ENDPOINTS = {
    # Expected to pass attestation and PCR verification.
    "match": "match.demo.genxt.network",
    # Negative test endpoint: its attestation should fail verification.
    "mismatch": "mismatch.demo.genxt.network",
}

def get_service_info(hostname, verify):
    """Fetch only public metadata; the caller decides whether it is trusted."""
    with httpx.Client(verify=verify, follow_redirects=False, timeout=10.0) as client:
        response = client.get(f"https://{hostname}/service-info")
        response.raise_for_status()
        service_info = response.json()
    if not isinstance(service_info, dict):
        raise ValueError("/service-info did not return a JSON object")
    return service_info


def setup_client(endpoint):
    """Show metadata, request consent, then attest before opening chat."""
    hostname = ENDPOINTS[endpoint]

    # This first request uses the demo's self-signed certificate without a
    # trust anchor. Its content is displayed only and never used for trust.
    preview = get_service_info(hostname, verify=False)
    print("\n" + "=" * 68)
    print(f"SERVICE INFO  |  {hostname}")
    print("=" * 68)
    print("Unverified preview: the HTTPS certificate has not been authenticated yet.")
    print("Treat these fields as display-only until TEE appraisal succeeds.\n")
    print(json.dumps(preview, indent=2, ensure_ascii=False))

    advertisement = preview.get("teeReport")
    nonce = advertisement.get("nonce") if isinstance(advertisement, dict) else None
    fields = advertisement.get("response") if isinstance(advertisement, dict) else None
    binding = advertisement.get("sessionBinding") if isinstance(advertisement, dict) else None
    supported = (
        isinstance(advertisement, dict)
        and advertisement.get("endpoint") == "/tee-report"
        and advertisement.get("method") == "POST"
        and isinstance(nonce, dict)
        and nonce.get("name") == "nonce"
        and nonce.get("in") == "body"
        and nonce.get("encoding") == "base64"
        and nonce.get("sizeBytes") == 32
        and isinstance(fields, dict)
        and fields.get("evidenceField") == "evidence"
        and fields.get("certificateField") == "certificate"
        and (binding is None or (isinstance(binding, dict) and binding.get("supported") is False))
    )
    if not supported:
        print("\nTEE report advertisement is missing or incompatible with this client.")
        print("Expected: POST /tee-report with a 32-byte base64 nonce in JSON.")
        print(f"Advertised: {json.dumps(advertisement, sort_keys=True)}")
        print("Chat was not opened.")
        return None

    print("\nTEE attestation report is available (advertised; not yet verified).")
    print(f"  Report: POST https://{hostname}/tee-report")
    print('  Body: {"nonce": "<fresh 32-byte base64 nonce>"}')
    print(f"  TRS configured: {TRS_SOURCE}")
    print("  TLS session binding: NOT SUPPORTED.")
    print("  The report is nonce- and certificate-bound, but not bound to this TLS session.")
    print("  IETF SEAT is drafting attestation-to-TLS binding:")
    print("  https://datatracker.ietf.org/wg/seat/documents/")
    print("  Exported Authenticators (RFC 9261) in BoringSSL are ongoing")
    print("  implementation work; session binding is not active in this demo.")
    print("  Appraisal: nonce, certificate binding, TEE evidence, PCRs, and IMA.")
    answer = input("\nRetrieve and appraise the report before chat? [Y/n]: ").strip().lower()
    if answer not in ("", "y", "yes"):
        print("Attestation skipped. Chat was not opened.")
        return None

    print("\nRetrieving a fresh TEE report and appraising it against the TRS...")
    # Keep Confido's detailed attestation trace visible after user confirmation.
    confido.atls_debug()
    try:
        # Confido generates a fresh nonce and verifies the returned evidence.
        atls_cert = confido.aTLS_connect_py(f"https://{hostname}", TRS_REGISTRY)
    except Exception as exc:
        print(f"TEE appraisal: FAILED — {exc}")
        print("Chat was not opened.")
        return None

    print("TEE appraisal: PASSED — TEE report and bound vTPM quote verified.")
    print("TEE–vTPM trust chain: confirmed.")
    print("  The vTPM attestation public key was extracted from the TEE report")
    print("  and used to verify the signed vTPM quote.")
    print("Execution environment: verified against the trusted manifest in the configured TRS.")
    print("Server certificate: bound to the verified TEE report.")

    # Trust only the certificate bound into the verified report.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
    context.load_verify_locations(cadata=atls_cert)

    verified_info = get_service_info(hostname, verify=context)
    if verified_info == preview:
        print("Service info: matches the preview when fetched with the verified certificate.")
    else:
        print("Service info: preview differed. Response fetched with the verified certificate:")
        print(json.dumps(verified_info, indent=2, ensure_ascii=False))

    print("Opening chat over HTTPS with the certificate bound to the verified report.\n")
    credential_file = Path(os.environ.get("CONFIDO_CREDENTIALS_FILE", Path(__file__).with_name(".credentials.json")))
    credentials = json.loads(credential_file.read_text()) if credential_file.exists() else {}
    username = os.environ.get("CONFIDO_USERNAME") or credentials.get("username")
    password = os.environ.get("CONFIDO_PASSWORD") or credentials.get("password")
    if not username or not password:
        raise ValueError("Set CONFIDO_USERNAME/CONFIDO_PASSWORD or provide a local .credentials.json file")
    http_client = httpx.Client(verify=context, auth=(username, password))
    return openai.OpenAI(
        api_key="null",
        base_url=f"https://{hostname}/v1",
        http_client=http_client,
    )

def chat_loop(client):
    """Run a chat session, then return to endpoint selection."""
    # Initialize conversation history
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    
    print("\nWelcome to the Interactive Chat!")
    print("Type 'exit' or 'quit' to return to endpoint selection")
    print("Type 'clear' to start a new conversation")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("\nYou > ").strip()
        
        # Check for exit commands
        if user_input.lower() in ['exit', 'quit']:
            print("\nChat ended. Returning to endpoint selection.")
            return
        
        # Check for clear command
        if user_input.lower() == 'clear':
            conversation = [{"role": "system", "content": "You are a helpful assistant."}]
            print("\nConversation cleared!")
            continue
        
        if not user_input:
            continue

        # Add user message to conversation history
        conversation.append({"role": "user", "content": user_input})
        
        try:
            # Get completion from the model
            completion = client.chat.completions.create(
                model="llama-default",
                messages=conversation
            )
            
            # Extract and print the response
            assistant_response = completion.choices[0].message.content
            print("\nAssistant:", assistant_response)
            
            # Add assistant's response to conversation history
            conversation.append({"role": "assistant", "content": assistant_response})
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try again.")

def main():
    print("\nConfido attestation chat demo")
    print("Before chat starts, Confido verifies the server's TEE evidence, vTPM PCRs, and IMA log.")
    print()
    print("TEE  = Trusted Execution Environment")
    print("TPM  = Trusted Platform Module (vTPM: virtual TPM); PCR = Platform Configuration Register")
    print("IMA  = Integrity Measurement Architecture")
    print(f"\nTrusted measurement source: {TRS_SOURCE}")

    while True:
        print("\nChoose an attestable endpoint to connect:")
        print("1. match.demo.genxt.network - expected successful verification")
        print("2. mismatch.demo.genxt.network - expected verification failure")
        print("0. Exit")
        choice = input("\nEndpoint [1]: ").strip() or "1"

        if choice == "0":
            print("\nGoodbye!")
            return

        endpoint = {"1": "match", "2": "mismatch"}.get(choice)
        if endpoint is None:
            print("Invalid endpoint choice. Please choose 0, 1, or 2.")
            continue

        try:
            client = setup_client(endpoint)
        except Exception as e:
            print(f"\nConnection or verification failed: {e}")
            continue

        if client is None:
            continue

        try:
            chat_loop(client)
        finally:
            client.close()

if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
