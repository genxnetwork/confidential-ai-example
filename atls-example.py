import confido, ssl, httpx, openai

confido.atls_debug()
atls_cert = confido.aTLS_connect_py("http://api.genxt.ai:8000")
print("aTLS Certificate: \n", atls_cert)

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_verify_locations(cadata=atls_cert)

username = 'peterromov'
password = '00be83b3ae30a8677ba798af4406187f077852d6'
http_client = httpx.Client(verify=context, auth=(username, password))

client = openai.OpenAI(
    api_key="null",
    base_url="https://api.genxt.ai/v1",
    http_client=http_client,
)

completion = client.chat.completions.create(
    model="llama2-uncensored:70b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message)



# logging.basicConfig(level=logging.DEBUG)
# httpx_logger = logging.getLogger("httpx")
# httpx_logger.setLevel(logging.DEBUG)
# httpx_logger.addHandler(logging.StreamHandler())