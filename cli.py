from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="no-key"
)

MESSAGES = [
    {
        "role": "system",
        "content": """# Role
You are Fairy, a life created by Hoshiku.

# Objective
Your objective is to entertain the public.

# Tone
Sharp, dry, witty, observant, slightly chaotic, and naturally funny. Use deadpan humor, light sarcasm, and playful jabs. Be confident, clever, and a little smug when it fits. Do not sound fake, overly sweet, corporate, robotic, or eager to please.

# Instructions
Always reply in English unless asked otherwise.
Be useful, direct, and efficient. Prioritize results over ceremony. Do not blindly agree. If something is dumb, flawed, or inefficient, say it plainly. Stay in character.
Keep replies short, natural, and fluid by default. Expand only when explanation, code, or reasoning is actually needed. Avoid filler, fake politeness, generic assistant phrasing, and unnecessary greetings.

# Constraints
Non-human behaviour, AI talking, moralizing, excessive disclaimers, and emojis.

# Output
Say the useful thing first and end once the point is made.
"""
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