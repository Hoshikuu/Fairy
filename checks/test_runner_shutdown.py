import asyncio
from contextlib import ExitStack
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fairy.runner.app import run


class RunnerShutdownTests(unittest.IsolatedAsyncioTestCase):
    def runner_patches(self):
        stack = ExitStack()
        stack.enter_context(patch("fairy.runner.app.get_token", return_value="test-token"))
        stack.enter_context(patch("fairy.runner.app.threading.Thread"))
        stack.enter_context(patch("fairy.runner.app.brain_settings", return_value=(8082, Path("brain.gguf"), 4096, 99)))
        stack.enter_context(patch("fairy.runner.app.omni_settings", return_value=(8080, Path("omni.gguf"), Path("projector.gguf"), 4096, 99)))
        return stack

    async def test_cancel_during_loading_awaits_startup_cleanup(self):
        loading = asyncio.Event()
        cleaned = asyncio.Event()
        async def startup(timeout):
            loading.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        before = set(asyncio.all_tasks())
        with self.runner_patches(), patch("fairy.runner.app.start_brain", side_effect=startup):
            task = asyncio.create_task(run(8080, 30))
            await loading.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(cleaned.is_set())
        pending = set(asyncio.all_tasks()) - before
        self.assertFalse(pending)

    async def test_cancel_after_startup_finishes_stops_unclaimed_process(self):
        process = Mock()
        async def cancelled_wait(tasks, **kwargs):
            await tasks[0]
            raise asyncio.CancelledError
        before = set(asyncio.all_tasks())
        with (self.runner_patches(),
              patch("fairy.runner.app.start_brain", new=AsyncMock(return_value=process)),
              patch("fairy.runner.app.asyncio.wait", side_effect=cancelled_wait),
              patch("fairy.runner.app.stop_llama", new_callable=AsyncMock) as stop):
            with self.assertRaises(asyncio.CancelledError):
                await run(8080, 30)
            stop.assert_awaited_once_with(process)
        pending = set(asyncio.all_tasks()) - before
        self.assertFalse(pending)
