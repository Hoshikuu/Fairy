from openai import AsyncOpenAI
from tool.read_system import system_prompt

client = AsyncOpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="no-key"
)

MESSAGES = [
    {
        "role": "system",
        "content": system_prompt()
    }
]

async def ask_req(message: str):

    MESSAGES.append(
        {
            "role": "user",
            "content": message
        }
    )

    response = await client.chat.completions.create(
        model="local-model",
        messages=MESSAGES,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}}
    )

    response_message = response.choices[0].message

    content = response_message.content or ""

    MESSAGES.append(
        {
            "role": "assistant",
            "content": content
        }
    )

    reasoning = getattr(
        response_message,
        "reasoning_content",
        None
    )

    if reasoning:
        print(
            f"Thinking: {reasoning.strip().replace(chr(10), ' ')}"
        )

    print(
        f"AI: {content.strip().replace(chr(10), ' ')}"
    )

    return content