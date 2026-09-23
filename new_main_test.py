from hada.hada_init import HADA
from hada.stt_init import STT
from hada.tts_init import speak
from hada.mem_init import Mem
from hada.monitor_init import Monitor
from time import sleep
from RealtimeSTT import AudioToTextRecorderClient
from os import devnull
from contextlib import redirect_stdout, redirect_stderr
from openai import OpenAI
from uuid import uuid4

if __name__ == "__main__":
    
    hada = HADA()

    print("cargando hada")

    hada.start()

    while not hada.setup:
        sleep(1)

    hada.client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="no-key"
    )

    stt = STT()

    print("cargando stt")

    stt.start()

    while not stt.setup:
        sleep(1)

    print("cargando tts")

    speak("Testeo", True)

    monitor = Monitor()
    monitor.run()

    print("iniciando cliente stt")

    if stt.recorder is None:
        # SILENCIAR EL MODULO
        with open(devnull, "w") as fnull:
            with redirect_stdout(fnull), redirect_stderr(fnull):
                stt.recorder = AudioToTextRecorderClient(
                    control_url="ws://127.0.0.1:8011",
                    data_url="ws://127.0.0.1:8012",
                    language="es",
                )

    _id = str(uuid4())
    mem = Mem(_id)

    try:
        while True:
            print()
            print("Recording ...")
            _in = stt.play()
            print(_in)
            response = hada.ask(_in, mem, monitor)
            _out = ""
            for text in response:
                speak(text)
                _out += text
            speak("", True)
            mem.Register(_in, _out)
            sleep(10)
    except KeyboardInterrupt:
        stt.stop()
        hada.stop()
