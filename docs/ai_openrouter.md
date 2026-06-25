### Contoh Penggunaan OpenRouter API

      from openrouter import OpenRouter
      import os
      
      with OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
      ) as client:
        response = client.chat.send(
          model="openrouter/owl-alpha",
          messages=[
            {
              "role": "user",
              "content": "What is the meaning of life?"
            }
          ]
        )
      
        print(response.choices[0].message.content)
            