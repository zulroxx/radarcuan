import json, os
from pathlib import Path
from dotenv import load_dotenv
from mistralai.client import Mistral

if __name__ == '__main__':
    load_dotenv(Path(__file__).parent / '.env')
    c = Mistral(api_key=os.environ["LLM_API_KEY"], server_url="https://api.mistral.ai")
    r = c.chat.complete(
        model="mistral-medium-latest",
        messages=[{"role":"user","content":"Katakan halo dalam JSON: {\"greeting\":\"...\"}"}],
        response_format={"type":"json_object"},
    )
    print("RAW:", repr(r.choices[0].message.content[:2000]))

