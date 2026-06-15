import json, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')
from mistralai.client import Mistral

c = Mistral(api_key=os.environ["LLM_API_KEY"], server_url="https://api.mistral.ai")
r = c.chat.complete(
    model="mistral-small-latest",
    messages=[{"role":"user","content":"Katakan halo dalam JSON: {\"greeting\":\"...\"}"}],
    response_format={"type":"json_object"},
)
print("RAW:", repr(r.choices[0].message.content[:2000]))
