#   ----------------------------------------------------
#          Hoshikuu - https://github.com/Hoshikuu
#   ----------------------------------------------------
#   HadaAI/hada/hada_init.py - V0.3.0

from subprocess import Popen as proc, PIPE, STDOUT, CREATE_NEW_PROCESS_GROUP, TimeoutExpired
from threading import Thread
from signal import CTRL_BREAK_EVENT
from datetime import datetime
import time
import openai

class HADA:
    def __init__(self, model: str = ""):
        self.model = model

        self.client = None

        self.setup = False

        self.start_key = "server is listening on"

    def log(self, text: str, extra: str = "unspecified"):
        """HADA MODULE Logger, logs the given text

        Args:
            text (str): The text to log
            extra (str, optional): The type of the log. Defaults to "unspecified".
        """
        with open(f"logs/hada-{datetime.now().date()}.log", "a", encoding="utf-8") as f:
            lines = text.split("\n")
            for line in lines:
                # Formato del logger
                # [CATEGORIA] [TIEMPO] [TEXTO]
                if line == "":
                    continue
                f.write(f"[{extra.upper()}] [{datetime.now().time()}] {line}\n")
        if extra.upper() == "ERROR":
            print("Ha ocurrido un error inesperado, consulta el log para mas informacion")

    def start(self):
        # llama.cpp/build/bin/Release/llama-server.exe --model hada/models/HadaAI/HadaAI-.gguf --alias Hoshiku/HadaAI --host 127.0.0.1 --port 8000 --ctx-size 16384 --predict 1024 --threads 6 --gpu-layers 12 --temp 0.7 --top-p 0.9 --top-k 40 --min-p 0.05 --presence-penalty 0.1 --repeat-penalty 1.1 --batch-size 2048 --ubatch-size 512 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --jinja --no-webui

        cmd = [
            'llama.cpp/build/bin/Release/llama-server.exe',
            '--model', f'hada/models/HadaAI/HadaAI-{self.model}.gguf',
            '--alias', 'Hoshiku/HadaAI',
            '--host', '127.0.0.1',
            '--port', '8000',
            '--ctx-size', '16384',
            '--predict', '1024',
            '--threads', '6',
            '--gpu-layers', '12',
            '--temp', '0.7',
            '--top-p', '0.9',
            '--top-k', '40',
            '--min-p', '0.05',
            '--presence-penalty', '0.1',
            '--repeat-penalty', '1.1',
            '--batch-size', '2048',
            '--ubatch-size', '512',
            '--flash-attn', 'on',
            '--cache-type-k', 'q8_0',
            '--cache-type-v', 'q8_0',
            '--jinja', '--no-webui'
        ]

        self.proc = proc(
            cmd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
            bufsize=1,
            creationflags=CREATE_NEW_PROCESS_GROUP
        )

        Thread(target=self.read, daemon=True).start()

    def ask(self, prompt, mem, monitor):
        if self.client is None:
            print("No client detected, Watch OpenAI")
            return None

        def system_prompt():
            with open(f"hada/prompts/system/hadaV7.txt", "r") as f:
                return f.read()

        messages = [
            {"role": "system", "content": system_prompt()},
        ]

        memories = mem.ReadMem()
        for memory in memories:
            messages.append(memory)
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model="Hoshiku/HadaAI",
            messages=messages,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            stream=True,
        )

        def response():
            tokens = 0
            ta = time.perf_counter()
            for chunk in stream:
                tokens += 1
                tb = time.perf_counter()
                tps = tokens / (tb - ta)
                monitor.pack(2, "Id", 12, [tokens, round(tps, 2)])
                text = chunk.choices[0].delta.content or ""
                print(text, end="", flush=True)
                yield text

        return response()

    def read(self):
        buffer = ""
        while self.proc and self.proc.poll() is None:
            char = self.proc.stdout.read(1)
            buffer += char

            if char == "\n":
                self.log(buffer, "info")
                buffer = ""

            line = buffer.lower()

            if self.start_key.lower() in line:
                self.setup = True
                break

    def stop(self):
        try:
            self.proc.send_signal(CTRL_BREAK_EVENT)
            self.proc.wait(timeout=5)
        except TimeoutExpired:
            self.proc.kill()

# if __name__ == "__main__":
#     hada = HADA()
#     hada.start()

#     try:
#         while True:
#             if not hada.setup:
#                 time.sleep(1)
#                 continue
#             print()
#             prompt = input("Escribe: ")
#             mem = Mem()
#             hada.ask(prompt, mem)
#     except KeyboardInterrupt:
#         hada.stop()
