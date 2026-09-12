import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

LLAMA_SERVER = PROJECT_ROOT / "llama" / "llama-server.exe"
MODEL = PROJECT_ROOT / "models" / "Spark-X2.5-4B-Q4_K_M.gguf"


process = subprocess.Popen(
    [
        str(LLAMA_SERVER),
        "-m", str(MODEL),
        '--alias', 'Hoshiku/HadaAI',
        '--host', '127.0.0.1',
        '--port', '8080',
        '--ctx-size', '16384',
        '--predict', '1024',
        '--threads', '8',
        '--gpu-layers', '99',
        '--temp', '1.0',
        '--top-p', '0.95',
        '--top-k', '-1',
        '--presence-penalty', '0.1',
        '--repeat_penalty', '1.1',
        '--frequency_penalty', "0.1",
        '--batch-size', '2048',
        '--ubatch-size', '512',
        '--flash-attn', 'on',
        '--cache-type-k', 'q8_0',
        '--cache-type-v', 'q8_0',
        '--jinja', '--no-webui'
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

print(f"llama-server iniciado con PID {process.pid}")

for line in process.stdout:
    print("[LLAMA]", line, end="")