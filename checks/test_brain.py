"""Offline tests for the MiniCPM adapter; no model or Discord connection."""

import asyncio
import unittest
from unittest.mock import patch

from fairy.ai.brain import BrainConfig, BrainSession, Tool, final_text, use_reasoning, validate_arguments


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


if __name__ == '__main__':
    unittest.main()
