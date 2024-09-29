import confido, ssl, httpx, openai
import argparse

# Set up the command-line argument parser
parser = argparse.ArgumentParser(description="Send a chat completion request to GENXT Confidential LLM Inference service.")
parser.add_argument('content', nargs='+', help='Content for the chat completion request. Multiple words can be provided separated by spaces.')

# Parse the arguments
args = parser.parse_args()
user_promt = ' '.join(args.content)

# Existing code for aTLS and HTTP setup
confido.atls_debug()
atls_cert = confido.aTLS_connect_py("http://api.genxt.ai:9000")
print("aTLS Certificate: \n", atls_cert)

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_verify_locations(cadata=atls_cert)

username = 'ELIXIR'
password = 'GA4GH-Connect-2024'
http_client = httpx.Client(verify=context, auth=(username, password))

client = openai.OpenAI(
    api_key="null",
    base_url="https://api.genxt.ai/v1",
    http_client=http_client,
)

# Use the user-provided content for the chat completion
completion = client.chat.completions.create(
    model="llama2-uncensored:70b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": user_promt
        }
    ]
)

print(completion.choices[0].message)
