"""HTTP contract checks without downloading or loading the speech model."""

import unittest
from concurrent.futures import ThreadPoolExecutor
import threading

from fastapi.testclient import TestClient

from kokoro_server import create_app


class FakeEngine:
    voice = "af_heart"
    device = "cpu"
    pipeline = None

    def __init__(self):
        self.loads = 0
        self.calls = []

    def load(self):
        self.loads += 1
        self.pipeline = object()

    def synthesize(self, text, voice, speed):
        self.calls.append((text, voice, speed))
        if text == "silent":
            raise ValueError("The text produced no speech")
        if text == "failure":
            raise RuntimeError("test inference failure")
        return b"RIFF-test-audio"


class KokoroServiceTests(unittest.TestCase):
    def test_lifespan_loads_once_and_returns_audio(self):
        engine = FakeEngine()
        with TestClient(create_app(engine)) as client:
            self.assertEqual(client.get("/health").json()["sample_rate"], 24000)
            for text in ("Hello", "World"):
                response = client.post("/v1/audio/speech", json={"input": text})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "audio/wav")
                self.assertEqual(response.content, b"RIFF-test-audio")
            self.assertEqual(engine.loads, 1)
            self.assertEqual(engine.calls, [("Hello", "af_heart", 1.0), ("World", "af_heart", 1.0)])
        self.assertIsNone(engine.pipeline)

    def test_bad_requests_do_not_reach_inference(self):
        engine = FakeEngine()
        with TestClient(create_app(engine)) as client:
            for payload in ({"input": " "}, {"input": "a" * 4001},
                            {"input": "Hello", "speed": 0},
                            {"input": "Hello", "response_format": "mp3"},
                            {"input": "Hello", "model": "tts-1"}):
                self.assertEqual(client.post("/v1/audio/speech", json=payload).status_code, 422)
            self.assertEqual(client.post("/v1/audio/speech", json={
                "input": "Hello", "voice": "../model.pt"
            }).status_code, 400)
            self.assertEqual(engine.calls, [])

    def test_inference_errors_release_capacity(self):
        engine = FakeEngine()
        with TestClient(create_app(engine)) as client:
            for _ in range(4):
                self.assertEqual(client.post("/v1/audio/speech", json={"input": "silent"}).status_code, 422)
            self.assertEqual(client.post("/v1/audio/speech", json={"input": "failure"}).status_code, 500)
            self.assertEqual(client.post("/v1/audio/speech", json={"input": "Hello"}).status_code, 200)

    def test_queue_rejects_excess_requests(self):
        engine = FakeEngine()
        entered = threading.Condition()
        release = threading.Event()
        started = []

        def blocked_synthesis(text, voice, speed):
            with entered:
                started.append(text)
                entered.notify_all()
            if not release.wait(10):
                raise RuntimeError("test request timed out")
            return b"RIFF-test-audio"

        engine.synthesize = blocked_synthesis
        with TestClient(create_app(engine)) as client, ThreadPoolExecutor(3) as pool:
            futures = [pool.submit(client.post, "/v1/audio/speech", json={"input": str(i)})
                       for i in range(3)]
            try:
                with entered:
                    self.assertTrue(entered.wait_for(lambda: len(started) == 3, timeout=5))
                response = client.post("/v1/audio/speech", json={"input": "extra"})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.headers["retry-after"], "2")
            finally:
                release.set()
            for future in futures:
                self.assertEqual(future.result(timeout=5).status_code, 200)


if __name__ == "__main__":
    unittest.main()
