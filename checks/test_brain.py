"""Offline tests for the MiniCPM adapter; no model or Discord connection."""

import asyncio
import os
import unittest
from unittest.mock import patch

from fairy.ai.brain import (BrainConfig, BrainSession, Tool, final_text, sanitize_for_speech, use_reasoning,
                            validate_arguments)


class Response:
    def __init__(self, result):
        self.result = result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def json(self):
        return {'choices': [{'message': self.result['message']}]}


class Client:
    def __init__(self, responses):
        self.responses = responses
        self.payloads = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def post(self, url, *, json):
        self.payloads.append((url, dict(json, messages=list(json['messages']))))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return Response(result)


class BrainTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = BrainConfig(reasoning='auto')

    async def test_history_and_thinking_isolation(self):
        client = Client([
            {'message': {'content': 'Hello', 'thinking': 'private'}},
            {'message': {'content': 'Answer'}}])
        session = BrainSession(self.config, 'Be kind')
        with patch('fairy.ai.brain.aiohttp.ClientSession', return_value=client):
            self.assertEqual(await session.respond_text('Hi'), 'Hello')
            self.assertEqual(await session.respond_text('Explain this code error'), 'Answer')
        self.assertFalse(client.payloads[0][1]['chat_template_kwargs']['enable_thinking'])
        self.assertTrue(client.payloads[1][1]['chat_template_kwargs']['enable_thinking'])
        self.assertTrue(client.payloads[0][0].endswith('/v1/chat/completions'))
        self.assertEqual(client.payloads[1][1]['messages'][1:3], [
            {'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello'}])
        self.assertNotIn('private', str(session.history))

    async def test_tool_roundtrip_and_rejection(self):
        calls = []
        async def handler(arguments):
            calls.append(arguments)
            return 'done'
        schema = {'type': 'object', 'properties': {'value': {'type': 'string'}}, 'required': ['value']}
        tool = Tool('safe', 'Safe example', schema, handler)
        client = Client([{'message': {'tool_calls': [
            {'function': {'name': 'safe', 'arguments': {'value': 'x'}}},
            {'function': {'name': 'unknown', 'arguments': {}}}]}},
            {'message': {'content': 'Finished'}}])
        with patch('fairy.ai.brain.aiohttp.ClientSession', return_value=client):
            result = await BrainSession(self.config, 'system', {'safe': tool}).respond_text('call')
        self.assertEqual(result, 'Finished')
        self.assertEqual(calls, [{'value': 'x'}])
        self.assertEqual(client.payloads[1][1]['messages'][-1]['content'], 'Tool call rejected or timed out.')

    async def test_failure_does_not_commit_turn(self):
        session = BrainSession(self.config, 'system')
        for failure in (TimeoutError(), ConnectionError()):
            with patch('fairy.ai.brain.aiohttp.ClientSession', return_value=Client([failure])):
                with self.assertRaises(type(failure)):
                    await session.respond_text('hello')
        self.assertEqual(session.history, [])

    async def test_concurrent_requests_keep_history_order(self):
        client = Client([{'message': {'content': 'one'}}, {'message': {'content': 'two'}}])
        session = BrainSession(self.config, 'system')
        with patch('fairy.ai.brain.aiohttp.ClientSession', return_value=client):
            self.assertEqual(await asyncio.gather(session.respond_text('first'), session.respond_text('second')), ['one', 'two'])
        self.assertEqual(client.payloads[1][1]['messages'][1]['content'], 'first')

    def test_reasoning_never_returned(self):
        self.assertEqual(final_text('<think>secret</think>Answer'), 'Answer')
        with self.assertRaises(RuntimeError):
            final_text('<think>secret')
        with self.assertRaises(RuntimeError):
            final_text('<think')
        with self.assertRaises(RuntimeError):
            final_text('<think>secret</think>')
        self.assertFalse(use_reasoning('off', 'code'))
        self.assertTrue(use_reasoning('on', 'hello'))

    def test_arguments_and_local_origin(self):
        schema = {'type': 'object', 'properties': {'n': {'type': 'integer'}}, 'required': ['n']}
        for value in ({'n': True}, {'n': 1, 'extra': 'x'}, {}):
            with self.assertRaises(ValueError):
                validate_arguments(schema, value)
        with self.assertRaises(ValueError):
            BrainConfig(url='http://example.com')

    def test_context_defaults_to_2048(self):
        self.assertEqual(BrainConfig().context, 2048)
        env = {key: value for key, value in os.environ.items() if not key.startswith('FAIRY_')}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(BrainConfig.from_env().context, 2048)
        with patch.dict(os.environ, dict(env, FAIRY_CONTEXT_SIZE='4096'), clear=True):
            self.assertEqual(BrainConfig.from_env().context, 4096)


class SpeechSanitizerTests(unittest.TestCase):
    def test_removes_emojis_and_symbols(self):
        self.assertEqual(sanitize_for_speech('Hello there \U0001F600\u2728!'), 'Hello there !')
        self.assertEqual(sanitize_for_speech('Hehe~ that is *so* cute~'), 'Hehe that is so cute')
        self.assertEqual(sanitize_for_speech('Sun \u2600\ufe0f and heart \u2764\ufe0f'), 'Sun and heart')
        self.assertEqual(sanitize_for_speech('Family \U0001F468\u200d\U0001F469\u200d\U0001F467 time'), 'Family time')

    def test_removes_markdown(self):
        self.assertEqual(sanitize_for_speech('## Title\n**Bold** and __under__ text'), 'Title Bold and under text')
        self.assertEqual(sanitize_for_speech('- first\n- second\n\u2022 third'), 'first second third')
        self.assertEqual(sanitize_for_speech('Run `pip check` now'), 'Run pip check now')
        self.assertEqual(sanitize_for_speech('```python\nprint(1)\n```'), 'print(1)')
        self.assertEqual(sanitize_for_speech('  many   spaces\n\nhere  '), 'many spaces here')

    def test_keeps_plain_punctuation(self):
        text = "It's 3:15; ready? Yes, well-known. Great!"
        self.assertEqual(sanitize_for_speech(text), text)

    def test_final_text_sanitizes_and_rejects_empty_output(self):
        self.assertEqual(final_text('<think>secret</think>**Sure** \U0001F60A'), 'Sure')
        for content in ('\U0001F600\U0001F389', '~~ ** ##', '\u2728 \u2764\ufe0f'):
            with self.assertRaises(RuntimeError):
                final_text(content)


if __name__ == '__main__':
    unittest.main()
