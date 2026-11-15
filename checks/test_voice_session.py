import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from fairy.voice.session import MIN_VOICE_BYTES, Speaker, VoiceSession


class VoiceSessionTests(unittest.IsolatedAsyncioTestCase):
    def make_session(self):
        return VoiceSession(Mock(), Mock(), "system", omni=Mock())

    async def test_flush_preserves_speaker_and_rejects_short_audio(self):
        session = self.make_session()
        session.speakers[1] = Speaker(bytearray(b"a" * MIN_VOICE_BYTES), MIN_VOICE_BYTES)
        session.speakers[2] = Speaker(bytearray(b"short"), 5)
        session.flush(1)
        session.flush(2)
        user_id, pcm = session.utterances.get_nowait()
        session.utterances.task_done()
        self.assertEqual(user_id, 1)
        self.assertEqual(len(pcm), MIN_VOICE_BYTES)
        self.assertTrue(session.utterances.empty())
        self.assertFalse(session.speakers)

    async def test_stop_releases_clients_and_queued_audio(self):
        session = self.make_session()
        client = AsyncMock()
        session.clients[1] = client
        session.frames.put_nowait((1, b"pcm"))
        session.utterances.put_nowait((1, b"pcm"))
        session.speakers[1] = Speaker()
        await session.stop()
        client.close.assert_awaited_once()
        self.assertFalse(session.clients)
        self.assertFalse(session.speakers)
        await asyncio.wait_for(session.frames.join(), 1)
        await asyncio.wait_for(session.utterances.join(), 1)

    async def test_interrupt_stops_playback_and_discards_pending_turns(self):
        session = self.make_session()
        session.current_client = AsyncMock()
        session.playback = Mock()
        session.utterances.put_nowait((2, b"pcm"))
        session.notice = AsyncMock()
        session.interrupt()
        await session.interrupt_task
        session.playback.stop.assert_called_once()
        session.current_client.cancel.assert_awaited_once()
        self.assertTrue(session.utterances.empty())
        self.assertTrue(session.cancel_complete.is_set())
