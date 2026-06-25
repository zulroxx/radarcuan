### Contoh codingan python
```
from groq import Groq

client = Groq()
completion = client.chat.completions.create(
    model="qwen/qwen3-32b",
    messages=[
      {
        "role": "user",
        "content": ""
      }
    ],
    temperature=1,
    max_completion_tokens=8192,
    top_p=1,
    reasoning_effort="high",
    stream=False,
    response_format={"type": "json_object"},
    stop=None,
    tools=[{"type":"code_interpreter"},{"type":"browser_search"}]
)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
```
