"""Check MiniCPM server process ownership without loading model weights."""

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fairy.runner.dual import start_brain


class BrainServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_is_started_with_native_template(self):
        process = MagicMock()
        with (patch('fairy.runner.dual.brain_settings', return_value=(8082, Path('model.gguf'), 4096, 12)),
              patch('pathlib.Path.is_file', return_value=True),
              patch('fairy.runner.dual.check_port') as port_check,
              patch('fairy.runner.dual.subprocess.Popen', return_value=process) as start,
              patch('fairy.runner.dual.wait_ready', new_callable=AsyncMock) as ready):
            self.assertIs(await start_brain(30), process)
        port_check.assert_called_once_with(8082)
        command = start.call_args.args[0]
        self.assertIn('--jinja', command)
        self.assertEqual(command[command.index('--port') + 1], '8082')
        ready.assert_awaited_once_with(process, 8082, 30, name='MiniCPM')

    async def test_failed_readiness_stops_owned_process(self):
        process = MagicMock()
        with (patch('fairy.runner.dual.brain_settings', return_value=(8082, Path('model.gguf'), 4096, 12)),
              patch('pathlib.Path.is_file', return_value=True),
              patch('fairy.runner.dual.check_port'),
              patch('fairy.runner.dual.subprocess.Popen', return_value=process),
              patch('fairy.runner.dual.wait_ready', new_callable=AsyncMock, side_effect=TimeoutError),
              patch('fairy.runner.dual.stop_llama', new_callable=AsyncMock) as stop):
            with self.assertRaises(TimeoutError):
                await start_brain(1)
            stop.assert_awaited_once_with(process)
