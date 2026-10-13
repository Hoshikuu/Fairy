from openai import AsyncOpenAI
from tool.read_system import system_prompt
import asyncio

client = AsyncOpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="no-key",
    timeout=60,
    max_retries=0,
)

MESSAGES = [
    {
        "role": "system",
        "content": system_prompt()
    }
]

request_lock = asyncio.Lock()


def new_history():
    return [{"role": "system", "content": system_prompt()}]


async def ask_req(message: str, *, history=None):
    """Send an OpenAI-compatible chat request to the local llama-server."""
    history = MESSAGES if history is None else history
    async with request_lock:
        user_message = {"role": "user", "content": message}

        response = await client.chat.completions.create(
            model="Hoshiku/HadaAI",
            messages=[*history, user_message],
            extra_body={"chat_template_kwargs": {"enable_thinking": False}}
        )

        response_message = response.choices[0].message

        content = response_message.content or ""

        # Commit only completed turns, so failed/cancelled requests do not
        # leave an unanswered user message in the conversation.
        history.extend([user_message, {"role": "assistant", "content": content}])

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
