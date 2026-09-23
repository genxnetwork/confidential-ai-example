"""Point-in-time evidence appraisal before a cooperating client opens chat."""
import confido
import os
from pathlib import Path
import json
import httpx
import openai
import uuid
from datetime import datetime, timezone

POLICY_DIR = Path(os.environ.get("CONFIDO_POLICY_DIR", Path(__file__).with_name("profiles")))
ENDPOINTS = {"match": "match.demo.genxt.network", "mismatch": "mismatch.demo.genxt.network"}


def load_policy(endpoint):
    return json.loads((POLICY_DIR / f"{endpoint}.json").read_text())


def reference_link(policy):
    ref = policy["reference"]
    return f'https://github.com/{ref["repository"]}/blob/{ref["commit"]}/{ref["path"]}'


class AppraisedTransport(httpx.BaseTransport):
    """All requests pass through Confido's private, origin-scoped HTTPS client."""
    def __init__(self, session):
        self.session = session

    def handle_request(self, request):
        status, headers, body = self.session.request(
            request.method, str(request.url), list(request.headers.multi_items()), request.read()
        )
        return httpx.Response(status, headers=headers, content=body, request=request)


def read_credentials():
    path = Path(os.environ.get("CONFIDO_CREDENTIALS_FILE", Path(__file__).with_name(".credentials.json")))
    credentials = json.loads(path.read_text()) if path.exists() else {}
    username = os.environ.get("CONFIDO_USERNAME") or credentials.get("username")
    password = os.environ.get("CONFIDO_PASSWORD") or credentials.get("password")
    if not username or not password:
        raise ValueError("Set CONFIDO_USERNAME/CONFIDO_PASSWORD or provide a local .credentials.json file")
    return username, password


def new_bundle_path(endpoint):
    root = Path(os.environ.get("CONFIDO_RUN_DIR", Path.home() / ".local/state/confido/runs"))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    run = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
    run.mkdir(mode=0o700)
    return run / f"{endpoint}.json"


def show_result(result):
    print("\nAPPRAISAL STAGES")
    print("-" * 68)
    for check in result["checks"]:
        print(f'  {check["status"].upper():6}  {check["stage"]}: {check["detail"]}')
    print(f'\nDecision: {result["status"].upper()} ({result["reason"]})')
    print(f'IMA coverage: {result["coverage"]["ima_entries"]} enrolled entries; boot aggregate and kernel modules.')
    print("Application/model files and GPU state are outside this measurement coverage.")


def setup_client(endpoint):
    """No application credentials are read until all required stages pass."""
    if getattr(confido, "__version__", None) != "0.3.0":
        raise RuntimeError("This demo requires the local Confido 0.3.0 wheel; run make dev-update")
    policy = load_policy(endpoint)
    config_json = json.dumps(policy)
    preview = json.loads(confido.discover_py(config_json))
    print("\n" + "=" * 68)
    print(f'SERVICE INFO  |  {policy["origin"]}')
    print("=" * 68)
    print("Bootstrap preview: the HTTPS peer has not been authenticated yet.")
    print("These fields are display-only until appraisal and HTTPS authentication pass.\n")
    print(json.dumps(preview, indent=2, ensure_ascii=True))
    ad = preview.get("teeReport", {})
    if ad.get("profile") != "azure-snp-vtpm-ima/1" or ad.get("wireVersion") != 1:
        print("\nTEE report advertisement is incompatible: profile/version upgrade required.")
        print("Chat was not opened.")
        return None
    print("\nTEE attestation report is available (advertised; not yet verified).")
    print(f'  Report: POST {policy["origin"]}/tee-report')
    print(f'  TRS configured: {reference_link(policy)}')
    print(f'  Reference SHA-256: {policy["reference"]["sha256"]}')
    print("  TLS session binding: NOT SUPPORTED.")
    print("  A fresh vTPM quote binds the nonce, certificate and IMA log.")
    print("  The SNP report is not necessarily regenerated for this request.")
    print("  RFC 9261 standardizes Exported Authenticators; IETF SEAT attestation")
    print("  integration remains draft work. BoringSSL integration is planned here.")
    print("  https://www.rfc-editor.org/rfc/rfc9261.html")
    print("  https://datatracker.ietf.org/wg/seat/documents/")
    answer = input("\nRetrieve and appraise the report before chat? [Y/n]: ").strip().lower()
    if answer not in ("", "y", "yes"):
        print("Appraisal skipped. Chat was not opened.")
        return None

    print("\nCollecting evidence and a fresh vTPM quote; appraising against the pinned reference...")
    confido.atls_debug()
    bundle_path = new_bundle_path(endpoint)
    session = confido.connect_py(config_json, json.dumps(preview), str(bundle_path))
    result = json.loads(session.result_json)
    show_result(result)
    print(f"Run record: {bundle_path.with_suffix('.result.json')}")
    if not result["application_admitted"]:
        print("Chat was not opened. No application request or credential was sent.")
        return None

    print("\nTEE report and bound vTPM quote: VERIFIED.")
    print("  The vTPM public key was extracted from SNP-authenticated HCL metadata")
    print("  and verified the quote signature: TEE → HCL → vTPM trust chain confirmed.")
    print("Measured boot and IMA state: matches the configured trusted reference.")
    print("HTTPS peer: authenticated using the certificate bound into the quote.")
    print("Service info: critical identity and report fields match the preview.")
    print("Inference: llama-default forwards to Azure-hosted inference outside this VM's appraisal boundary.")
    print("Opening chat after successful environment appraisal and HTTPS authentication.\n")
    # Read secrets only after Confido exposes the admitted session.
    credentials = read_credentials()
    http_client = httpx.Client(transport=AppraisedTransport(session), auth=credentials,
                              follow_redirects=False, timeout=30.0)
    return openai.OpenAI(api_key="null", base_url=f'{policy["origin"]}/v1',
                         http_client=http_client, max_retries=0)

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
    print("\nConfido evidence-appraisal chat demo")
    print("Before chat, Confido verifies TEE/HCL evidence, a fresh vTPM quote, PCRs and the IMA log.")
    print()
    print("TEE  = Trusted Execution Environment")
    print("TPM  = Trusted Platform Module (vTPM: virtual TPM); PCR = Platform Configuration Register")
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
        except Exception as exc:
            print(f"\nRequest withheld: {exc}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
