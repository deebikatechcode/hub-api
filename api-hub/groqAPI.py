import os
from groq import AsyncGroq

client = AsyncGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

async def groqAPI(messages, model) -> str:
    chat_completion = await client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stop=None,
        stream=False,
    )
    return chat_completion.choices[0].message.content
