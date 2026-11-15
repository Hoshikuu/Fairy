"""Desktop session and bridge behavior without hardware or models."""

import asyncio
import base64
import ctypes
import io
import json
import os
import struct
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fairy.ai.brain import validate_arguments
from fairy.desktop import control
from fairy.desktop.bridge import Bridge
from fairy.desktop.control import desktop_tools
from fairy.desktop.session import DesktopSession, split_speech_sentences
from fairy.desktop.vtube import VTubeClient


def events(bridge: Bridge) -> list[dict]:
    return [json.loads(line) for line in bridge.output.getvalue().splitlines()]


async def call(tool, arguments: dict) -> str:
    """Run a tool exactly like BrainSession: validate first, then call the handler."""
    return await tool.handler(validate_arguments(tool.parameters, arguments))


def fake_user32(left: int = 0, top: int = 0, width: int = 2560, height: int = 1440) -> MagicMock:
    user = MagicMock()
    user.GetSystemMetrics.side_effect = {76: left, 77: top, 78: width, 79: height}.__getitem__
    user.SetCursorPos.return_value = 1
    user.SendInput.side_effect = lambda count, _array, _size: count
    return user


class DesktopTests(unittest.IsolatedAsyncioTestCase):
    async def test_turn_transcribes_speaks_and_cancel_restores_history(self):
        omni = AsyncMock()
        omni.transcribe.return_value = "Hello"
        omni.speak = AsyncMock()
        session = DesktopSession(omni, "prompt")
        session.brain.respond_text = AsyncMock(return_value="Hi")
        result = await session.respond(pcm=b"\0\0", on_audio=AsyncMock())
        self.assertEqual(result, "Hi")
        session.brain.respond_text.assert_awaited_once_with("Unverified ASR transcript: Hello")
        omni.speak.assert_awaited_once()

        session.brain.history = [{"role": "user", "content": "previous"}]
        started = asyncio.Event()
        async def slow(_text):
            session.brain.history.append({"role": "user", "content": "partial"})
            started.set()
            await asyncio.Event().wait()
        session.brain.respond_text = slow
        task = asyncio.create_task(session.respond(text="test", on_audio=AsyncMock()))
        await started.wait()
        await session.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(session.brain.history, [{"role": "user", "content": "previous"}])
        await session.close()

    async def test_bridge_validates_screen_and_resets(self):
        bridge = Bridge(io.StringIO())
        frame = base64.b64encode(b"\xff\xd8\xfftest\xff\xd9").decode()
        await bridge.command({"type": "frame", "data": frame})
        self.assertEqual(bridge.current_frame(), frame)
        await bridge.command({"type": "clear_frame"})
        self.assertIsNone(bridge.current_frame())
        with self.assertRaises(ValueError):
            await bridge.command({"type": "frame", "data": base64.b64encode(b"bad").decode()})
        bridge.emit("status", message="ready")
        self.assertEqual(json.loads(bridge.output.getvalue())["message"], "ready")

    async def test_concurrent_turn_rejected(self):
        session = DesktopSession(AsyncMock(), "prompt")
        started = asyncio.Event()
        async def slow(_text):
            started.set()
            await asyncio.Event().wait()
        session.brain.respond_text = slow
        first = asyncio.create_task(session.respond(text="first", on_audio=AsyncMock()))
        await started.wait()
        with self.assertRaises(RuntimeError):
            await session.respond(text="second", on_audio=AsyncMock())
        await session.cancel()
        await asyncio.gather(first, return_exceptions=True)
        await session.close()


class SpeechStreamingTests(unittest.IsolatedAsyncioTestCase):
    def test_split_speech_sentences(self):
        self.assertEqual(split_speech_sentences("Hi"), ["Hi"])
        self.assertEqual(split_speech_sentences("  Hi there.  "), ["Hi there."])
        self.assertEqual(split_speech_sentences("Okay. Sure. That works for me today."),
                         ["Okay. Sure. That works for me today."])
        parts = split_speech_sentences("This is the first full sentence. Here comes the second one! "
                                       "And is this the third and final sentence?")
        self.assertEqual(parts, ["This is the first full sentence.", "Here comes the second one!",
                                 "And is this the third and final sentence?"])
        text = "A long opening sentence for the reply. Fine. Another complete closing sentence."
        self.assertEqual(" ".join(split_speech_sentences(text)), text)
        for part in split_speech_sentences(text):
            self.assertGreaterEqual(len(part), 20)

    async def test_multi_sentence_reply_streams_each_sentence_in_order(self):
        omni = AsyncMock()
        spoken = []
        async def speak(text, callback):
            spoken.append(text)
            await callback(b"\0\0")
        omni.speak.side_effect = speak
        session = DesktopSession(omni, "prompt")
        answer = "This is the first full sentence. Here comes the second one! And is this the final sentence?"
        session.brain.respond_text = AsyncMock(return_value=answer)
        on_audio = AsyncMock()
        self.assertEqual(await session.respond(text="talk", on_audio=on_audio), answer)
        self.assertEqual(spoken, split_speech_sentences(answer))
        self.assertEqual(omni.speak.await_count, 3)
        self.assertEqual(on_audio.await_count, 3)
        await session.close()


class BridgeVTubeTests(unittest.IsolatedAsyncioTestCase):
    def test_constructor_is_offline(self):
        with patch("fairy.desktop.vtube.aiohttp.ClientSession") as client_session:
            bridge = Bridge(io.StringIO())
        client_session.assert_not_called()
        self.assertIsInstance(bridge.vtube, VTubeClient)
        self.assertFalse(bridge.vtube_enabled)
        self.assertFalse(bridge.control_enabled)
        self.assertEqual(bridge.output.getvalue(), "")

    async def test_vtube_command_toggles(self):
        bridge = Bridge(io.StringIO())
        await bridge.command({"type": "vtube", "enabled": True})
        self.assertTrue(bridge.vtube_enabled)
        await bridge.command({"type": "vtube", "enabled": "yes"})
        self.assertFalse(bridge.vtube_enabled)
        await bridge.command({"type": "vtube", "enabled": True})
        await bridge.command({"type": "vtube", "enabled": False})
        self.assertFalse(bridge.vtube_enabled)
        await bridge.command({"type": "control", "enabled": True})
        self.assertTrue(bridge.control_enabled)
        with self.assertRaises(ValueError):
            await bridge.command({"type": "unknown"})

    async def test_start_registers_all_tools(self):
        bridge = Bridge(io.StringIO())
        bridge.stopping.set()
        env = {key: value for key, value in os.environ.items() if not key.startswith("FAIRY_")}
        with (patch.dict(os.environ, env, clear=True),
              patch("fairy.desktop.bridge.omni_settings", return_value=(8080, Path("o"), Path("p"), 2048, 99)),
              patch("fairy.desktop.bridge.brain_settings", return_value=(8082, Path("b"), 2048, 20)),
              patch("fairy.desktop.bridge.start_brain", new_callable=AsyncMock, return_value=MagicMock()),
              patch("fairy.desktop.bridge.start_omni", new_callable=AsyncMock, return_value=MagicMock()),
              patch("fairy.desktop.bridge.OmniClient", return_value=AsyncMock())):
            await bridge.start()
        self.assertEqual(events(bridge)[-1]["type"], "ready")
        tools = bridge.session.brain.tools
        for name in ("desktop_click", "desktop_key", "desktop_type", "desktop_scroll", "media_control",
                     "get_current_time", "get_active_windows", "get_system_stats", "read_clipboard",
                     "remember_fact", "recall_facts", "set_expression"):
            self.assertIn(name, tools)
            self.assertEqual(tools[name].name, name)
        tools["set_expression"].handler  # bound to the bridge client
        with patch.object(bridge.vtube, "set_expression", AsyncMock(return_value="Expression set to happy.")):
            self.assertEqual(await call(tools["set_expression"], {"expression": "happy"}), "Expression set to happy.")
        self.assertEqual(events(bridge)[-1], {"type": "expression", "expression": "happy"})
        await bridge.session.close()

    async def run_turn(self, bridge: Bridge, chunks: list[bytes]) -> None:
        async def respond(*, text, pcm, on_audio, frame_provider):
            for chunk in chunks:
                await on_audio(chunk)
            return "Done."
        bridge.session = MagicMock()
        bridge.session.respond = respond
        await bridge.answer({"type": "turn", "text": "hello"})

    async def test_lip_sync_follows_audio_and_resets(self):
        loud = struct.pack("<h", 20000) * 960
        bridge = Bridge(io.StringIO())
        bridge.vtube = AsyncMock()
        await self.run_turn(bridge, [loud])
        bridge.vtube.set_mouth_open.assert_not_awaited()

        bridge.vtube_enabled = True
        await self.run_turn(bridge, [loud, bytes(1920)])
        values = [item.args[0] for item in bridge.vtube.set_mouth_open.await_args_list]
        self.assertEqual(values[0], 1.0)
        self.assertEqual(values[1:], [0.0, 0.0])
        self.assertEqual(events(bridge)[-1], {"type": "answer", "text": "Done."})

    async def test_vtube_errors_never_interrupt_speech(self):
        bridge = Bridge(io.StringIO())
        bridge.vtube = AsyncMock()
        bridge.vtube.set_mouth_open.side_effect = RuntimeError("VTube Studio closed")
        bridge.vtube_enabled = True
        await self.run_turn(bridge, [b"\0\0", b"\0\0"])
        kinds = [event["type"] for event in events(bridge)]
        self.assertEqual(kinds, ["audio", "audio", "answer"])
        self.assertIsNone(bridge.turn)


class DesktopControlTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enabled = True
        self.notes: list[str] = []
        self.tools = desktop_tools(lambda: self.enabled, self.notes.append)

    def test_schemas_are_accepted_by_validator(self):
        for name, tool in self.tools.items():
            for spec in tool.parameters["properties"].values():
                self.assertEqual(set(spec) - {"type", "description", "enum"}, set(), name)
        self.assertEqual(self.tools["desktop_click"].parameters["required"], ["x", "y"])
        self.assertEqual(ctypes.sizeof(control.Input), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)

    async def test_click_scales_capture_coordinates(self):
        cases = [
            ({"x": 640, "y": 360, "screen_width": 1280, "screen_height": 720}, (0, 0, 2560, 1440), (1280, 720)),
            ({"x": 100, "y": 50}, (0, 0, 2560, 1440), (100, 50)),
            ({"x": 0, "y": 0, "screen_width": 1280, "screen_height": 720}, (-1920, 0, 4480, 1440), (-1920, 0)),
            ({"x": 1279, "y": 719, "screen_width": 1280, "screen_height": 720}, (0, 0, 1920, 1080), (1918, 1078)),
        ]
        for arguments, desktop, expected in cases:
            user = fake_user32(*desktop)
            with (patch.object(control.sys, "platform", "win32"),
                  patch.object(control, "_user32", return_value=user)):
                self.assertEqual(await call(self.tools["desktop_click"], arguments), "Clicked.")
            user.SetCursorPos.assert_called_once_with(*expected)
            self.assertEqual([item.args[0] for item in user.mouse_event.call_args_list], [2, 4])

    async def test_click_rejects_outside_or_invalid_sizes(self):
        for arguments in ({"x": 1280, "y": 0, "screen_width": 1280, "screen_height": 720},
                          {"x": 3000, "y": 10}, {"x": -1, "y": 10},
                          {"x": 10, "y": 10, "screen_width": 0, "screen_height": 720},
                          {"x": 10, "y": 10, "screen_width": 1280, "screen_height": -720}):
            user = fake_user32()
            with (patch.object(control.sys, "platform", "win32"),
                  patch.object(control, "_user32", return_value=user)):
                with self.assertRaises(ValueError, msg=arguments):
                    await call(self.tools["desktop_click"], arguments)
            user.SetCursorPos.assert_not_called()
        with self.assertRaises(ValueError):
            await call(self.tools["desktop_click"], {"x": 1, "y": 1, "screen_width": "1280"})

    async def test_new_tools_are_gated_when_control_is_disabled(self):
        self.enabled = False
        calls = {"desktop_click": {"x": 1, "y": 1}, "desktop_key": {"key": "enter"},
                 "desktop_type": {"text": "hello"}, "desktop_scroll": {"clicks": -3},
                 "media_control": {"action": "play_pause"}}
        with (patch.object(control.sys, "platform", "win32"),
              patch.object(control, "_user32") as user):
            for name, arguments in calls.items():
                self.assertEqual(await call(self.tools[name], arguments), control.DISABLED, name)
        user.assert_not_called()
        self.assertEqual(self.notes, [])
        self.enabled = True
        with (patch.object(control.sys, "platform", "linux"), patch.object(control, "_user32") as user):
            for name, arguments in calls.items():
                self.assertEqual(await call(self.tools[name], arguments), control.DISABLED, name)
        user.assert_not_called()

    async def test_enabled_type_scroll_and_media(self):
        user = fake_user32()
        with (patch.object(control.sys, "platform", "win32"),
              patch.object(control, "_user32", return_value=user)):
            self.assertEqual(await call(self.tools["desktop_type"], {"text": "Hi\nyo"}), "Typed.")
            self.assertEqual(await call(self.tools["desktop_scroll"], {"clicks": -3}), "Scrolled.")
            self.assertEqual(await call(self.tools["media_control"], {"action": "next_track"}), "Media key pressed.")
            for arguments in ({"text": ""}, {"text": "x" * 201}, {"text": "bad\x07"}):
                with self.assertRaises(ValueError):
                    await call(self.tools["desktop_type"], arguments)
            for clicks in (21, -21):
                with self.assertRaises(ValueError):
                    await call(self.tools["desktop_scroll"], {"clicks": clicks})
            with self.assertRaises(ValueError):
                await call(self.tools["media_control"], {"action": "stop"})
        self.assertEqual(user.SendInput.call_args.args[0], 10)
        flags, _x, _y, delta, _extra = user.mouse_event.call_args.args
        self.assertEqual(flags, 0x0800)
        self.assertEqual(ctypes.c_int32(delta).value, -360)
        self.assertEqual([item.args[0] for item in user.keybd_event.call_args_list], [0xB0, 0xB0])
        self.assertEqual(control.MEDIA_KEYS, {"play_pause": 0xB3, "next_track": 0xB0, "prev_track": 0xB1,
                                              "volume_up": 0xAF, "volume_down": 0xAE, "volume_mute": 0xAD})
        self.assertEqual(len(self.notes), 3)


if __name__ == "__main__":
    unittest.main()
