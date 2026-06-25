### Contoh Penggunaan Mistral API

import os

from mistralai.client import Mistral

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

inputs = [
        {
            "role": "user",
            "content": "Hello!"
        }
    ]

completion_args = {
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 1
}

tools = []

response = client.beta.conversations.start(
    inputs=inputs,
    model="mistral-medium-latest",
    instructions="",
    completion_args=completion_args,
    tools=tools,
)

print(response)