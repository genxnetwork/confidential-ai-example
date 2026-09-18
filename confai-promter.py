import confido
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

def setup_client(endpoint):
    """Initialize and return the OpenAI client with proper configuration"""
    hostname = ENDPOINTS[endpoint]
    # Set up aTLS connection
    confido.atls_debug()
    atls_cert = confido.aTLS_connect_py(f"http://{hostname}:8000", TRS_REGISTRY)
    
    # Configure SSL context
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = False
    context.load_verify_locations(cadata=atls_cert)
    
    # Set up HTTP client with authentication
    username = 'ELIXIR'
    password = 'GA4GH-Connect-2024'
    http_client = httpx.Client(verify=context, auth=(username, password))
    
    # Initialize OpenAI client
    return openai.OpenAI(
        api_key="null",
        base_url=f"https://{hostname}/v1",
        http_client=http_client,
    )

def chat_loop(client):
    """Run the interactive chat loop"""
    # Initialize conversation history
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    
    print("\nWelcome to the Interactive Chat!")
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'clear' to start a new conversation")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("\nYou > ").strip()
        
        # Check for exit commands
        if user_input.lower() in ['exit', 'quit']:
            print("\nGoodbye!")
            break
        
        # Check for clear command
        if user_input.lower() == 'clear':
            conversation = [{"role": "system", "content": "You are a helpful assistant."}]
            print("\nConversation cleared!")
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
    print("Before chat starts, Confido verifies the server's TEE evidence, PCRs, and IMA measurements.")
    print(f"Trusted measurement source: {TRS_SOURCE}")
    print("\nChoose an endpoint to attest:")
    print("1. match.demo.genxt.network - expected successful verification")
    print("2. mismatch.demo.genxt.network - expected verification failure")
    choice = input("\nEndpoint [1]: ").strip() or "1"
    endpoint = {"1": "match", "2": "mismatch"}.get(choice)
    if endpoint is None:
        print("Invalid endpoint choice")
        return

    try:
        # Initialize the client
        client = setup_client(endpoint)
        
        # Start the chat loop
        chat_loop(client)
        
    except Exception as e:
        print(f"Failed to initialize: {str(e)}")
        return

if __name__ == "__main__":
    main()
