# Fairy

Execute `python setup.py` to install llama, Whisper, their models, and Kokoro.

## Servicio Kokoro TTS

Kokoro se ejecuta en un proceso y entorno propios (`.venv-kokoro`), separados
del bot y de sus dependencias. Necesita Python 3.10–3.13; se recomienda 3.12.
Si ya tienes instalados Whisper y llama, instala solamente Kokoro:

```powershell
python setup/kokoro_setup.py
```

El instalador descarga PyTorch para CPU, las dependencias de
`requirements-kokoro.txt`, el modelo de inglés de spaCy, Kokoro-82M y la voz
`af_heart`. Los pesos quedan en `models/kokoro` (o en `HF_HOME` si lo defines).
La primera instalación necesita Internet. Después se reutiliza la caché.

El arranque habitual inicia los tres servicios y espera sus comprobaciones
`/health`. Un fallo de arranque o la salida de un servicio detiene los demás;
`Ctrl+C` o `q` + Enter los cierra juntos:

```powershell
python llama_start.py
```

| Servicio | Puerto predeterminado | Endpoint |
| --- | --- | --- |
| llama | 8080 | `/v1/chat/completions` |
| Whisper | 8081 | `/inference` |
| Kokoro | 8082 | `/v1/audio/speech` |

Kokoro carga el modelo una sola vez y sintetiza una frase de calentamiento antes
de aceptar peticiones. Se ejecuta en CPU con cuatro hilos por defecto para
reservar la GPU a llama. Configuración opcional:

```powershell
python llama_start.py --kokoro-port 8082 --kokoro-voice af_heart --kokoro-threads 4
python llama_start.py --check
```

Puedes elegir voces inglesas americanas (`af_heart`, `am_adam`, etc.) o británicas
(`bf_emma`, etc.) con `--kokoro-voice`. Una voz diferente se descarga al iniciar
por primera vez. `--kokoro-python` permite usar otro entorno preparado.
`--kokoro-device cuda` requiere instalar una versión de PyTorch con CUDA en ese
entorno; el instalador suministra la versión CPU.

También puedes ejecutar solamente el TTS:

```powershell
.\.venv-kokoro\Scripts\python.exe kokoro_server.py
```

El endpoint recibe JSON con los campos habituales del formato de voz OpenAI y
devuelve un WAV PCM de 16 bits, mono, a 24 kHz. En esta versión acepta únicamente
`model: kokoro`, `response_format: wav` y la voz configurada al arrancar.
`input` admite de 1 a 4000 caracteres y `speed` de 0.5 a 2.0.
Hay una síntesis simultánea y hasta dos peticiones esperando; el exceso recibe
HTTP 503. La documentación interactiva está en `http://127.0.0.1:8082/docs`.

Prueba desde otra terminal:

```powershell
$speechBody = @{
    model = 'kokoro'
    input = 'Hello! I am Fairy.'
    voice = 'af_heart'
    speed = 1.0
    response_format = 'wav'
} | ConvertTo-Json
Invoke-WebRequest -Uri 'http://127.0.0.1:8082/v1/audio/speech' `
    -Method Post -ContentType 'application/json' -Body $speechBody -OutFile 'speech.wav'
```

Las respuestas generadas a partir de voz se envían a Kokoro y se reproducen en
el mismo canal de Discord. El bot convierte el WAV mono de 24 kHz a PCM estéreo
de 48 kHz en memoria, sin FFmpeg. Una cola de hasta ocho respuestas impide que
se solapen y permite que Whisper siga transcribiendo mientras Fairy habla.
Las respuestas largas se dividen en fragmentos de hasta 1000 caracteres.

## Voice transcription

Install the bot dependencies with `python -m pip install -r requirements.txt`.
The voice receiver uses a pinned DAVE-compatible fork of `discord-ext-voice-recv`
and `discord.py` 2.7. Do not install the original receiver alongside the fork.

Start the local Whisper server with the multilingual model (the default port
8081 avoids conflicting with llama-server on port 8080):

```powershell
python llama_start.py
```

Leave all three services running, then start the bot in a second terminal:

```powershell
python bot.py
```

Run `/join` in a server while you are in a voice channel. Fairy listens to all
human users in that channel and posts each transcription, identified by speaker,
in the text channel where `/join` was run. Audio from overlapping speakers is
kept separate. A phrase is sent to Whisper after 0.8 seconds of silence; continuous
speech is split into chunks of up to 15 seconds. The bot needs permission to
connect and speak in voice, and send messages in the selected text channel.
The bot must not be server-muted. Stage channels are not supported.

Use `/leave` from the same voice channel to stop transcription and disconnect.
The final buffered phrases are processed during shutdown (up to 10 seconds).
Audio is processed in memory, without saving recordings. Transcription runs
asynchronously; a bounded queue reports lost fragments if Whisper falls behind.
The bot also reports server and reception errors in the text channel.

Optional `.env` settings:

```dotenv
WHISPER_URL=http://127.0.0.1:8081
KOKORO_URL=http://127.0.0.1:8082
# Optional: if set, this must match --kokoro-voice in llama_start.py.
# KOKORO_VOICE=af_heart
KOKORO_SPEED=1.0
```

The bot always transcribes English (`en`), without automatic language detection.
Every non-empty transcription is also sent to the local llama-server at
`http://127.0.0.1:8080/v1/chat/completions`, using the OpenAI chat format:
`model`, `messages` with `system`/`user`/`assistant` roles, and the existing
`chat_template_kwargs` configuration. Start llama-server (for example with
`python llama_start.py`) before starting the bot.

Fairy speaks the model's response in the voice channel using Kokoro. Text commands
(`/ask` and mentions) continue to receive text replies.
Voice conversation history is separate for each speaker and voice session, with
the last 20 exchanges retained. Whisper and llama requests have separate bounded
queues so model generation does not block audio transcription. Kokoro synthesis
and playback use their own queue. Model errors and
queue overload are reported in the text channel. `/leave` allows up to 10 seconds
to finish pending transcription work before cancellation. Playback, pending
speech and in-flight TTS requests are cancelled immediately on `/leave`.

### Si Fairy no habla

1. Reinicia el bot después de actualizar el código y usa `/join` de nuevo.
2. Ejecuta `llama_start.py` y espera el mensaje de que los tres servicios están listos.
3. Consulta `http://127.0.0.1:8082/health`: debe indicar `status: ok` y `model: kokoro`.
4. Si cambias `--kokoro-port`, cambia también `KOKORO_URL` en el `.env` del bot.
   Si defines `KOKORO_VOICE`, debe coincidir con la voz del servicio; si lo omites,
   se utiliza automáticamente la voz configurada en el servicio.
5. Comprueba los permisos Conectar/Hablar y que el bot no esté silenciado por el servidor.
6. Los fallos de síntesis o reproducción aparecen en el canal de texto y con
   detalles en la consola del bot. Una cola llena se informa en el canal.
