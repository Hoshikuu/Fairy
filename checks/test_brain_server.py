"""Check MiniCPM server process ownership without loading model weights."""

import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fairy.runner.dual import brain_settings, omni_settings, start_brain, start_omni, use_draft


def clean_env(**values: str) -> dict[str, str]:
    """Return the current environment without Fairy overrides, plus explicit values."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('FAIRY_')}
    env.update(values)
    return env


def flag_value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


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

    async def start_brain_command(self, env: dict[str, str], is_file=None) -> list[str]:
        with (patch.dict(os.environ, env, clear=True),
              patch('pathlib.Path.is_file', autospec=True, side_effect=is_file or (lambda _path: True)),
              patch('fairy.runner.dual.check_port'),
              patch('fairy.runner.dual.subprocess.Popen', return_value=MagicMock()) as start,
              patch('fairy.runner.dual.wait_ready', new_callable=AsyncMock)):
            await start_brain(30)
        return start.call_args.args[0]

    async def test_default_brain_is_vram_optimized_without_draft(self):
        env = clean_env()
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(use_draft())
            port, _model, context, layers = brain_settings()
        self.assertEqual((port, context, layers), (8082, 2048, 20))
        # The draft model must not be required when speculative decoding is off.
        command = await self.start_brain_command(env, lambda path: 'DSpark' not in path.name)
        self.assertNotIn('-md', command)
        self.assertNotIn('--spec-type', command)
        self.assertNotIn('-ngld', command)
        self.assertEqual(flag_value(command, '-fa'), 'on')
        self.assertEqual(flag_value(command, '-ctk'), 'q8_0')
        self.assertEqual(flag_value(command, '-ctv'), 'q8_0')
        self.assertEqual(flag_value(command, '-ngl'), '20')
        self.assertEqual(flag_value(command, '-c'), '2048')
        self.assertEqual(flag_value(command, '--host'), '127.0.0.1')

    async def test_draft_is_opt_in(self):
        for value in ('1', 'true', 'YES', 'on'):
            with patch.dict(os.environ, clean_env(FAIRY_USE_DRAFT=value), clear=True):
                self.assertTrue(use_draft(), value)
        for value in ('0', 'false', 'no', ''):
            with patch.dict(os.environ, clean_env(FAIRY_USE_DRAFT=value), clear=True):
                self.assertFalse(use_draft(), value)
        command = await self.start_brain_command(clean_env(FAIRY_USE_DRAFT='1'))
        self.assertIn('-md', command)
        self.assertEqual(flag_value(command, '--spec-type'), 'draft-dspark')
        self.assertEqual(flag_value(command, '-ngld'), '20')
        self.assertEqual(flag_value(command, '-ctk'), 'q8_0')

    async def test_draft_enabled_requires_draft_file(self):
        with self.assertRaises(RuntimeError):
            await self.start_brain_command(clean_env(FAIRY_USE_DRAFT='1'), lambda path: 'DSpark' not in path.name)

    async def test_gpu_layers_and_context_can_be_overridden(self):
        env = clean_env(FAIRY_BRAIN_GPU_LAYERS='99', FAIRY_CONTEXT_SIZE='4096', FAIRY_OMNI_CONTEXT='4096')
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(brain_settings()[2:], (4096, 99))
            self.assertEqual(omni_settings(8080)[3], 4096)

    async def test_omni_uses_flash_attention_and_quantized_cache(self):
        env = clean_env()
        with patch.dict(os.environ, env, clear=True):
            port, _model, _projector, context, layers = omni_settings(8080)
        self.assertEqual((port, context, layers), (8080, 2048, 99))
        with (patch.dict(os.environ, env, clear=True),
              patch('pathlib.Path.is_file', return_value=True),
              patch('fairy.runner.dual.check_port') as port_check,
              patch('fairy.runner.dual.subprocess.Popen', return_value=MagicMock()) as start,
              patch('fairy.runner.dual.wait_ready', new_callable=AsyncMock) as ready):
            await start_omni(30, 8080)
        port_check.assert_called_once_with(8080)
        command = start.call_args.args[0]
        self.assertEqual(flag_value(command, '-fa'), 'on')
        self.assertEqual(flag_value(command, '-ctk'), 'q8_0')
        self.assertEqual(flag_value(command, '-ctv'), 'q8_0')
        self.assertEqual(flag_value(command, '-c'), '2048')
        self.assertEqual(flag_value(command, '--host'), '127.0.0.1')
        self.assertIn('--mmproj', command)
        self.assertEqual(ready.await_args.kwargs['name'], 'LFM3')


if __name__ == '__main__':
    unittest.main()
