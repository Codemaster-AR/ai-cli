import os
from groq import Groq

client = Groq(
    api_key="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")

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of low latency LLMs"
        }
    ], model="llama-3.3-70b-versatile")

print(chat_completion.choices[0].message.content)
