import asyncio
import json
import unittest
from unittest.mock import patch

import httpx
from openai import AsyncOpenAI, InternalServerError

import cli


class LlamaClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_http_request_and_completed_history(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 0,
                "model": "Hoshiku/HadaAI",
                "choices": [{"index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": "Hello Alice"
                }}],
            })

        async with AsyncOpenAI(
            base_url="http://127.0.0.1:8080/v1", api_key="no-key", max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False),
        ) as client:
            history = [{"role": "system", "content": "Be helpful"}]
            with patch("cli.client", client), patch("cli.request_lock", asyncio.Lock()):
                response = await cli.ask_req("My name is Alice", history=history)
        self.assertEqual(response, "Hello Alice")
        self.assertEqual(str(requests[0].url), "http://127.0.0.1:8080/v1/chat/completions")
        body = json.loads(requests[0].content)
        self.assertEqual(body["model"], "Hoshiku/HadaAI")
        self.assertEqual(body["messages"], [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "My name is Alice"},
        ])
        self.assertFalse(body["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(history[-1], {"role": "assistant", "content": "Hello Alice"})

    async def test_failed_request_does_not_change_history(self):
        async with AsyncOpenAI(
            base_url="http://127.0.0.1:8080/v1", api_key="no-key", max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(500, json={"error": "unavailable"})
            ), trust_env=False),
        ) as client:
            history = [{"role": "system", "content": "Be helpful"}]
            with patch("cli.client", client), patch("cli.request_lock", asyncio.Lock()):
                with self.assertRaises(InternalServerError):
                    await cli.ask_req("Hello", history=history)
        self.assertEqual(history, [{"role": "system", "content": "Be helpful"}])
