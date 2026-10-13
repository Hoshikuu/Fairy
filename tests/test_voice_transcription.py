import asyncio
import io
import struct
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from voice_transcription import TranscriptionSink, Utterance, VoiceTranscription
from whisper_client import transcribe_pcm


def frame(amplitude=1000):
    return SimpleNamespace(pcm=struct.pack("<hh", amplitude, amplitude) * 960)


def speaker(user_id, bot=False):
    return SimpleNamespace(id=user_id, bot=bot)


class AudioTests(unittest.TestCase):
    def test_overlapping_speakers_remain_separate_and_resample(self):
        sink = TranscriptionSink()
        for _ in range(10):
            sink.write(speaker(1), frame(1000))
            sink.write(speaker(2), frame(2000))
        sink.cleanup()
        chunks = [sink.utterances.get_nowait(), sink.utterances.get_nowait()]
        self.assertEqual([chunk.user_id for chunk in chunks], [1, 2])
        for chunk, amplitude in zip(chunks, (1000, 2000)):
            self.assertEqual(len(chunk.pcm), 6400)  # 200 ms of mono 16 kHz PCM.
            self.assertEqual(set(struct.unpack("<3200h", chunk.pcm)), {amplitude})

    def test_silence_and_bots_do_not_generate_transcriptions(self):
        sink = TranscriptionSink()
        for _ in range(10):
            sink.write(speaker(1), frame(0))
            sink.write(speaker(2, bot=True), frame())
            sink.write(None, frame())
        sink.cleanup()
        self.assertTrue(sink.utterances.empty())

    def test_pause_flushes_phrase_even_without_more_packets(self):
        sink = TranscriptionSink()
        with patch("voice_transcription.time.monotonic", return_value=10):
            for _ in range(10):
                sink.write(speaker(1), frame())
        with patch("voice_transcription.time.monotonic", return_value=11):
            sink.flush_silence()
        self.assertEqual(sink.utterances.get_nowait().user_id, 1)
        self.assertFalse(sink.buffers)
        sink.cleanup()

    def test_continuous_speech_is_bounded_and_backlog_is_reported(self):
        sink = TranscriptionSink(max_seconds=0.2)
        for _ in range(650):
            sink.write(speaker(1), frame())
        self.assertEqual(sink.utterances.qsize(), 64)
        self.assertEqual(sink.dropped, 1)
        self.assertLess(len(sink.buffers[1].pcm), sink.max_bytes)
        sink.cleanup()


class TranscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_whisper_receives_correct_wav_and_language(self):
        pcm = struct.pack("<h", 1000) * 1600
        captured = {}

        def respond(request):
            captured["request"] = request
            return httpx.Response(200, json={"text": " Hola mundo. "})

        real_client = httpx.AsyncClient
        transport = httpx.MockTransport(respond)
        with patch("whisper_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(
            transport=transport, **kwargs
        )):
            text = await transcribe_pcm(pcm, server_url="http://whisper.test", language="es")
        self.assertEqual(text, "Hola mundo.")
        request = captured["request"]
        self.assertEqual(str(request.url), "http://whisper.test/inference")
        self.assertIn(b'\r\n\r\nes\r\n', request.content)
        wav_start = request.content.index(b"RIFF")
        with wave.open(io.BytesIO(request.content[wav_start:]), "rb") as wav:
            self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getsampwidth()), (1, 16000, 2))
            self.assertEqual(wav.readframes(wav.getnframes()), pcm)

    async def test_bad_whisper_response_is_an_error(self):
        real_client = httpx.AsyncClient
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        with patch("whisper_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(
            transport=transport, **kwargs
        )):
            with self.assertRaises(RuntimeError):
                await transcribe_pcm(b"\0\0" * 1600)

    async def test_stop_flushes_last_phrase_and_posts_without_pings(self):
        client = SimpleNamespace(listen=lambda *args, **kwargs: None, stop_listening=lambda: None)
        channel = SimpleNamespace(send=AsyncMock())
        session = VoiceTranscription(
            client, channel, asyncio.Lock(), server_url="http://whisper.test", language="auto"
        )
        with patch("voice_transcription.transcribe_pcm", new=AsyncMock(return_value="Hello @everyone")), patch(
            "voice_transcription.ask_req", new=AsyncMock(return_value="Hello there")
        ) as llama:
            session.start()
            for _ in range(10):
                session.sink.write(speaker(123), frame())
            await session.stop()
        self.assertEqual(channel.send.await_count, 2)
        llama.assert_awaited_once()
        self.assertEqual(llama.call_args.args[0], "Hello @everyone")
        self.assertIn("Fairy", channel.send.call_args.args[0])
        self.assertIn("<@123>", channel.send.call_args.args[0])
        mentions = channel.send.call_args.kwargs["allowed_mentions"].to_dict()
        self.assertEqual(mentions["parse"], [])
        self.assertFalse(session.tasks)

    async def test_voice_llama_histories_are_separate_for_each_speaker(self):
        channel = SimpleNamespace(send=AsyncMock())
        session = VoiceTranscription(
            SimpleNamespace(), channel, asyncio.Lock(), server_url="http://whisper.test", language="en"
        )
        for user_id, text in ((1, "My name is Alice"), (2, "My name is Bob"), (1, "What is my name?")):
            session.llm_queue.put_nowait((user_id, text))
        session.transcription_done.set()
        calls = []

        async def respond(text, *, history):
            calls.append((text, list(history)))
            history.extend([{"role": "user", "content": text}, {"role": "assistant", "content": "OK"}])
            return "OK"

        with patch("voice_transcription.ask_req", side_effect=respond):
            await session._llm_loop()
        self.assertEqual(len(calls[1][1]), 1)  # Bob starts with only the system prompt.
        self.assertEqual(calls[2][1][1]["content"], "My name is Alice")
        self.assertNotIn("My name is Bob", str(calls[2][1]))
        self.assertEqual(channel.send.await_count, 3)
        session.sink.cleanup()

    async def test_llama_failure_is_reported_and_next_phrase_is_processed(self):
        channel = SimpleNamespace(send=AsyncMock())
        session = VoiceTranscription(
            SimpleNamespace(), channel, asyncio.Lock(), server_url="http://whisper.test", language="en"
        )
        session.llm_queue.put_nowait((1, "First phrase"))
        session.llm_queue.put_nowait((2, "Second phrase"))
        session.transcription_done.set()
        with patch("voice_transcription.ask_req", new=AsyncMock(
            side_effect=[RuntimeError("llama offline"), "Second answer"]
        )):
            with self.assertLogs("voice_transcription", level="ERROR"):
                await session._llm_loop()
        self.assertEqual(channel.send.await_count, 2)
        self.assertIn("llama-server", channel.send.call_args_list[0].args[0])
        self.assertIn("Second answer", channel.send.call_args.args[0])
        session.sink.cleanup()

    async def test_whisper_failure_is_reported_and_worker_survives(self):
        channel = SimpleNamespace(send=AsyncMock())
        session = VoiceTranscription(
            SimpleNamespace(stop_listening=lambda: None), channel, asyncio.Lock(),
            server_url="http://whisper.test", language="auto",
        )
        session.sink.utterances.put_nowait(Utterance(1, b"\0\0" * 1600))
        session.sink.utterances.put_nowait(Utterance(2, b"\0\0" * 1600))
        session.sink.cleanup()
        with patch("voice_transcription.transcribe_pcm", new=AsyncMock(
            side_effect=[httpx.ConnectError("offline"), "Segunda frase"]
        )):
            with self.assertLogs("voice_transcription", level="ERROR"):
                await session._transcribe_loop()
        self.assertEqual(channel.send.await_count, 2)
        self.assertIn("Segunda frase", channel.send.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
