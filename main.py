# ----------------------------------------------------
# Hoshikuu - https://github.com/Hoshikuu
# ----------------------------------------------------
# HadaAI/main.py - V0.2.2

from asyncio import run, sleep, create_task, get_event_loop, CancelledError
from openai import OpenAI
from hada import Hada, Stt, Mem

from hada.tts_init import speak

def HadaPrompt(version: str, default: str = "5"):
    """Reads the Hada System Prompt

    Args:
        version (str): The version of Hada System Prompt.
        default (str, optional): Fallback version if the specified version is wrong. Defaults to version 5.

    Returns:
        str: The content of that specific version
    """
    if version == None or version == "":
        version = default

    try:
        with open(f"hada/prompts/system/hadaV{version}.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        with open(f"hada/prompts/system/hadaV{default}.txt", "r") as f:
            return f.read()
    except Exception as e:
        print("Error inesperado en HadaPrompt()", e)

def QueryHada(prompt: str, mem: Mem):
    """Query to ask to Hada.

    Si se pasa una instancia de Tts, la respuesta se habla en tiempo real
    mientras el stream de tokens se genera (latencia mínima).

    Args:
        prompt (str): The prompt string to pass it to Hada
        mem    (Mem): The memory class initialized in main
        tts    (Tts): TTS module (opcional). Si None, solo imprime.

    Returns:
        str: The response of Hada
    """
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="no-key"
    )

    memories = mem.ReadMem()
    messages = [{"role": "system", "content": HadaPrompt("7")}]
    for memory in memories:
        messages.append(memory)
    messages.append({"role": "user", "content": prompt})

    stream = client.chat.completions.create(
        model="Hoshiku/HadaAI",
        messages=messages,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        stream=True,
    )

    response = ""

    # Generator que imprime Y alimenta el TTS al mismo tiempo

    for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        print(text, end="", flush=True)
        response += text

    speak(response)
    return response

async def main():
    """Async main function
    """
    # Inicializa los módulos
    hada = Hada(model="")
    stt  = Stt()
    mem  = Mem()

    speak("aaaaaa")

    loop = get_event_loop()

    # Crea las tareas para ejecutar Hada y Stt
    task_hada = create_task(hada.StartHada())
    task_stt  = create_task(stt.StartStt())

    # Si el programa te abre un CMD ejecutando el STT, intenta aumentar este sleep para darle tiempo al stt a inicarse
    await sleep(10)
    #TODO Solucionar este tipo de cosas para hacer una espera dinamica segun lo que tarde en inicarse los modulos

    try:
        while True:
            prompt = await loop.run_in_executor(None, stt.Play)
            await sleep(1)
            if prompt is None:
                print(prompt)
                break
            print(prompt)
            # Pasa tts a QueryHada para que Hada hable mientras genera
            response = await loop.run_in_executor(None, QueryHada, prompt, mem)
            mem.Register(prompt, response)

    except (KeyboardInterrupt, CancelledError):
        pass

    finally:
        stt.StopStt()
        await task_stt
        hada.StopHada()
        await task_hada

if __name__ == "__main__":
    """Main function
    """
    try:
        run(main())
    except KeyboardInterrupt:
        pass