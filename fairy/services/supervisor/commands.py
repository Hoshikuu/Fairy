"""Build argv for the three local service processes."""

from __future__ import annotations

from fairy.config.paths import LLAMA_SERVER, WHISPER_SERVER


def build_commands(args):
    whisper_command = [
        str(WHISPER_SERVER),
        "--model", str(args.whisper_model.resolve()),
        "--host", args.host,
        "--port", str(args.whisper_port),
        "--language", "en",
        "--no-gpu",
        "--threads", "4",
    ]
    llama_command = [
        str(LLAMA_SERVER),
        "--model", str(args.llama_model.resolve()),
        "--alias", "Hoshiku/HadaAI",
        "--host", args.host,
        "--port", str(args.llama_port),
        "--ctx-size", "16384",
        "--predict", "1024",
        "--threads", "8",
        "--gpu-layers", str(args.llama_gpu_layers),
        "--batch-size", "2048",
        "--ubatch-size", "512",
        "--flash-attn", "on",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--jinja",
        "--no-webui",
    ]

    kokoro_command = [str(args.kokoro_python), "-u", "-m", "fairy.services.kokoro",
                      "--host", args.host, "--port", str(args.kokoro_port),
                      "--voice", args.kokoro_voice, "--device", args.kokoro_device,
                      "--threads", str(args.kokoro_threads)]
    return whisper_command, llama_command, kokoro_command
