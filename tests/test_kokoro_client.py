import asyncio
import io
import json
import struct
import threading
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from kokoro_client import DiscordPCM, FRAME_BYTES, check_kokoro, play_wav, speech_chunks, synthesize_wav
from voice_transcription import VoiceTranscription


def wav_bytes(frames=2400, rate=24000, channels=1):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(struct.pack("<h", 1000) * frames * channels)
    return output.getvalue()


class PCMTests(unittest.TestCase):
    def test_resampling_stereo_frames_and_end_of_audio(self):
        source = DiscordPCM(wav_bytes())
        frames = []
        while frame := source.read():
            self.assertEqual(len(frame), FRAME_BYTES)
            samples = struct.unpack("<1920h", frame)
            self.assertEqual(samples[::2], samples[1::2])
            frames.append(frame)
        self.assertEqual(len(frames), 5)
        self.assertTrue(any(frames))
        source.cleanup()
        self.assertEqual(source.read(), b"")

    def test_rejects_wrong_sample_rate_and_empty_audio(self):
        for wav in (wav_bytes(rate=16000), wav_bytes(channels=2), wav_bytes(frames=0)):
            with self.assertRaises(ValueError):
                DiscordPCM(wav)

    def test_long_responses_fit_service_and_keep_all_text(self):
        text = "Hello world. " * 400
        chunks = list(speech_chunks(text))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1000 for chunk in chunks))
        self.assertEqual(" ".join(chunks), text.strip())


class FakeVoice:
    def __init__(self, auto_finish=True):
        self.auto_finish = auto_finish
        self.source = None
        self.started = asyncio.Event()
        self.stopped = False
        self.frames = []

    def play(self, source, *, after):
        self.source = source
        self.after = after
        self.started.set()
        if self.auto_finish:
            def consume():
                while frame := source.read():
                    self.frames.append(frame)
                after(None)
            threading.Thread(target=consume).start()

    def stop_playing(self):
        self.stopped = True
        self.after(None)
        self.source = None


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_and_voice_mismatch(self):
        real_client = httpx.AsyncClient
        with patch("kokoro_client.httpx.AsyncClient", side_effect=lambda **kw: real_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
                "status": "ok", "model": "kokoro", "voice": "bf_emma"
            })), **kw
        )):
            await check_kokoro(server_url="http://kokoro.test")
            with self.assertRaisesRegex(ValueError, "KOKORO_VOICE"):
                await check_kokoro(voice="af_heart")

    async def test_http_contract_and_server_voice_default(self):
        def handler(request):
            self.assertEqual(str(request.url), "http://kokoro.test/v1/audio/speech")
            body = json.loads(request.content)
            self.assertEqual(body["input"], "Hello")
            self.assertEqual(body["response_format"], "wav")
            self.assertNotIn("voice", body)
            return httpx.Response(200, content=wav_bytes(), headers={"Content-Type": "audio/wav"})
        real_client = httpx.AsyncClient
        with patch("kokoro_client.httpx.AsyncClient", side_effect=lambda **kw: real_client(
            transport=httpx.MockTransport(handler), **kw
        )):
            audio = await synthesize_wav("Hello", server_url="http://kokoro.test/")
        self.assertEqual(audio, wav_bytes())

    async def test_http_errors_and_non_audio_are_not_played(self):
        real_client = httpx.AsyncClient
        for response, error in ((httpx.Response(503), httpx.HTTPStatusError),
                                (httpx.Response(200, json={}), ValueError)):
            with patch("kokoro_client.httpx.AsyncClient", side_effect=lambda **kw: real_client(
                transport=httpx.MockTransport(lambda request: response), **kw
            )):
                with self.assertRaises(error):
                    await synthesize_wav("Hello")

    async def test_playback_completes_from_other_thread(self):
        voice = FakeVoice()
        await play_wav(voice, wav_bytes())
        self.assertEqual(len(voice.frames), 5)
        self.assertTrue(voice.stopped)

    async def test_cancel_playback_stops_sender(self):
        voice = FakeVoice(auto_finish=False)
        task = asyncio.create_task(play_wav(voice, wav_bytes()))
        await asyncio.wait_for(voice.started.wait(), timeout=2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(voice.stopped)

    async def test_voice_answer_reaches_kokoro_and_playback_in_order(self):
        channel = SimpleNamespace(send=AsyncMock())
        session = VoiceTranscription(FakeVoice(), channel, asyncio.Lock(), server_url="x", language="en")
        session.llm_queue.put_nowait((1, "Hello"))
        session.llm_queue.put_nowait((2, "Hi"))
        session.transcription_done.set()
        synth = AsyncMock(return_value=wav_bytes())
        with patch("voice_transcription.ask_req", new=AsyncMock(side_effect=["Answer one", "Answer two"])), \
                patch("voice_transcription.synthesize_wav", new=synth):
            await asyncio.gather(session._llm_loop(), session._speech_loop())
        self.assertEqual([call.args[0] for call in synth.call_args_list], ["Answer one", "Answer two"])
        self.assertEqual(channel.send.await_count, 0)
        self.assertEqual(len(session.voice_client.frames), 10)
        self.assertTrue(session.speech_queue.empty())
        session.sink.cleanup()

    async def test_tts_failure_does_not_discard_next_answer(self):
        session = VoiceTranscription(FakeVoice(), SimpleNamespace(send=AsyncMock()),
                                     asyncio.Lock(), server_url="x", language="en")
        session.speech_queue.put_nowait((1, "First"))
        session.speech_queue.put_nowait((2, "Second"))
        session.llm_done.set()
        with patch("voice_transcription.synthesize_wav", new=AsyncMock(
            side_effect=[httpx.ConnectError("offline"), wav_bytes()]
        )):
            with self.assertLogs("voice_transcription", level="ERROR"):
                await session._speech_loop()
        self.assertEqual(len(session.voice_client.frames), 5)
        self.assertEqual(session.text_channel.send.await_count, 1)
        self.assertIn("Kokoro", session.text_channel.send.call_args.args[0])
        session.sink.cleanup()

    async def test_leave_cancels_current_synthesis_and_discards_backlog(self):
        voice = SimpleNamespace(stop_listening=lambda: None)
        session = VoiceTranscription(voice, SimpleNamespace(send=AsyncMock()),
                                     asyncio.Lock(), server_url="x", language="en")
        session.speech_queue.put_nowait((1, "First"))
        session.speech_queue.put_nowait((2, "Second"))
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def blocked(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with patch("voice_transcription.synthesize_wav", side_effect=blocked):
            session.speech_task = asyncio.create_task(session._speech_loop())
            await asyncio.wait_for(started.wait(), 2)
            await session.stop()
        self.assertTrue(cancelled.is_set())
        self.assertTrue(session.speech_queue.empty())
        await asyncio.wait_for(session.speech_queue.join(), 1)


if __name__ == "__main__":
    unittest.main()
