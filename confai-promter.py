import confido
import ssl
import httpx
import openai
import argparse

def setup_client():
    """Initialize and return the OpenAI client with proper configuration"""
    # Set up aTLS connection
    confido.atls_debug()
    atls_cert = confido.aTLS_connect_py("http://api.genxt.ai:9000")
    print("aTLS Certificate established")
    
    # Configure SSL context
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_verify_locations(cadata=atls_cert)
    
    # Set up HTTP client with authentication
    username = 'ELIXIR'
    password = 'GA4GH-Connect-2024'
    http_client = httpx.Client(verify=context, auth=(username, password))
    
    # Initialize OpenAI client
    return openai.OpenAI(
        api_key="null",
        base_url="https://api.genxt.ai/v1",
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
        user_input = input("\nYou: ").strip()
        
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
                model="llama2-uncensored:70b",
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
    try:
        # Initialize the client
        client = setup_client()
        
        # Start the chat loop
        chat_loop(client)
        
    except Exception as e:
        print(f"Failed to initialize: {str(e)}")
        return

if __name__ == "__main__":
    main()
