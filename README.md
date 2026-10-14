# Fairy

Bot de Discord con Whisper, llama.cpp y Kokoro locales. Referencia: Python 3.12.
La aplicación valida Python 3.11–3.12 por `asyncio.timeout` y Kokoro 0.9.4.

## Instalación

Desde la raíz, con un Python operativo:

```powershell
python setup.py --yes
python setup.py --check --verify-models
```

Setup prepara `.venv` para el bot y `.venv-kokoro` para TTS. Instala los
requisitos correspondientes, descarga componentes que falten y comprueba
dependencias, binarios, modelos y puertos. Los binarios existentes se conservan
salvo `--force`. `--verify-models` verifica SHA-256 del catálogo GGUF/GGML.

```powershell
python setup.py --only bot
python setup.py --only kokoro --kokoro-voice af_heart
python setup.py --only whisper --backend cpu --yes
python setup.py --check
python setup.py --check --only kokoro --warmup
```

`--warmup` carga Kokoro y sintetiza una frase; puede descargar pesos o una voz
que falten en caché. No combines los archivos de requisitos de ambos entornos.

## Un único arranque

Define `TOKEN` en `.env` y ejecuta:

```powershell
python main.py
```

El padre lanza `fairy.start`, espera a que los tres servicios estén listos y
después lanza `fairy.bot`. Sus entradas están en `fairy/start.py` y `fairy/bot.py`.
El supervisor utiliza `.venv-kokoro`; el bot utiliza `.venv`.

`q` + Enter o `Ctrl+C` solicita cierre conjunto. Primero cierra Discord y después
los servicios. Si un proceso termina inesperadamente, cierra el resto con
esperas limitadas y terminación de respaldo.

```powershell
python main.py --check
python main.py --kokoro-port 9082 --kokoro-voice bf_emma
python main.py --bot-python ./.venv/Scripts/python.exe
```

`--check` comprueba configuración, paquetes, Opus, binarios y puertos sin login.
El padre propaga las URL/puertos y voz al bot. `--startup-timeout` debe ser
finito y positivo; su valor predeterminado es 360 segundos.

## Entradas independientes

Para diagnóstico de un componente:

```powershell
python -m fairy.start
./.venv/Scripts/python.exe -m fairy.bot
./.venv/Scripts/python.exe -m fairy.bot --check
./.venv-kokoro/Scripts/python.exe -m fairy.services.kokoro
```

También se admiten `python fairy/start.py` y `python fairy/bot.py`.
Para uso normal utiliza `main.py`.

El cliente WAV anterior ahora se ejecuta como
`python -m fairy.clients.whisper_cli audio.wav` (mono PCM16/16 kHz).

## Estructura

```text
main.py                   Arranque conjunto
setup.py                  Instalación y comprobaciones
fairy/
  start.py, bot.py         Entradas de servicios y Discord
  runtime/                Orquestación, entornos y cierre
  config/                 Rutas, entorno y prompt
  clients/                HTTP
  audio/                  PCM, buffers y reproducción
  voice/                  Sesiones y trabajadores
  discord_bot/            Eventos, comandos y permisos
  services/               Supervisor y API/motor Kokoro
  installers/             Instalación y utilidades comunes
  diagnostics/            Comprobación real de la pipeline
prompt/system.txt         Prompt
docs/                     Operación y verificación
.learnings/               Registros HEAL
```

Se eliminaron `scripts/`, `tests/`, `setup/` y `tool/`. No hay adaptadores en
esas rutas. El código de aplicación importa desde `fairy/`.

## Servicios y voz

| Servicio | Puerto | Endpoint |
| --- | --- | --- |
| llama | 8080 | `/v1/chat/completions` |
| Whisper | 8081 | `/inference` |
| Kokoro | 8082 | `/v1/audio/speech` |

`/join` conecta al canal del usuario. Whisper transcribe en inglés por usuario,
llama responde y Kokoro reproduce la respuesta. Las transcripciones aparecen
por texto y las respuestas de voz se reproducen en orden. `/leave` cancela
síntesis/audio y desconecta. `/ask` y las menciones siguen respondiendo por texto.

Se necesitan Conectar/Hablar, permiso para enviar transcripciones y que el bot
no esté silenciado por el servidor. Los canales Stage no están soportados.
Kokoro usa CPU, cuatro hilos y `af_heart` por defecto.

Su API acepta `model: kokoro`, `input`, `voice` opcional, `speed` de 0.5 a 2.0 y
`response_format: wav`. Devuelve WAV PCM16 mono/24 kHz. Documentación en
`http://127.0.0.1:8082/docs`.

Configuración para ejecución independiente:

```dotenv
TOKEN=tu_token_de_discord
LLAMA_URL=http://127.0.0.1:8080/v1
WHISPER_URL=http://127.0.0.1:8081
KOKORO_URL=http://127.0.0.1:8082
KOKORO_SPEED=1.0
# Opcional; debe coincidir con la voz del servicio:
# KOKORO_VOICE=af_heart
```

## Verificación

```powershell
python -m compileall -q fairy main.py setup.py
git diff --check
python main.py --check
python setup.py --check --verify-models
./.venv/Scripts/python.exe -m pip check
./.venv-kokoro/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe -u -m fairy.diagnostics.voice_pipeline
```

El último comando prueba modelos reales hasta Opus en puertos temporales y
cierra los servicios. No se conecta a Discord. La suite permanente de `tests/`
se eliminó según la reorganización solicitada.

Consulta `ARCHITECTURE.md`, `docs/RUNBOOK.md` y `docs/VERIFICATION.md`.
La comprobación audible en una llamada real sigue pendiente.
