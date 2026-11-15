## [HEAL-20261031-005] sherpa Kokoro lexicon and cancellation

**Status**: verified
**Pattern-Key**: sherpa2.kokoro_lexicon; windows.asyncio_cancel_pipes
**Trigger**: Kokoro returned no audio because sherpa-onnx 2.0 ignores the previous espeak data directory. Cancellation also left Windows pipe transports unclosed.
**Diagnosis**: Version 2 requires a lexicon or external phonemizer; cancelling communicate requires draining child pipes after termination.
**Fix**: Configure the official English lexicon and call communicate after killing the child.
**Verification**: Kokoro generated 144096 PCM bytes for an English sentence. Cancellation produced no audio and exited without pipe warnings. Discord playback was not tested.
**Recurrence-Count**: 1

## HEAL-20261108-002: Electron binary installation

**Status**: verified
**Trigger**: npm installed the package without its Electron executable
**Diagnosis**: npm reported the Electron postinstall was not approved; approving and rebuilding still left the executable absent in this environment.
**Fix**: Downloaded the official Electron 39.8.10 Windows x64 archive, checked its SHA-256 against the package manifest, extracted it into the ignored Electron installation and wrote its path marker. `main.py --check` now checks the executable itself.
**Verification**: The checked executable started the Fairy window and loaded both local models. The UI automation service was unavailable.
**Pattern-Key**: electron.postinstall_missing_binary
**Recurrence-Count**: 1

## HEAL-20261108-003: Desktop bridge shutdown

**Status**: verified
**Trigger**: A real bridge test exited with Windows status 3221225477; a forced Electron exit also left model processes alive.
**Fix**: Stop the input reader on shutdown, close the Electron pipe and put the bridge and its children in a Windows job that terminates them on bridge exit.
**Verification**: A real text-to-speech turn returned 192000 PCM bytes and bridge exit 0. A separate forced-bridge test confirmed that both temporary model ports closed.
**Pattern-Key**: desktop.bridge_owned_process_shutdown
**Recurrence-Count**: 1

## [HEAL-20261014-001] missing_kokoro_discord_output

**Logged**: 2026-10-14
**Status**: verified
**Trigger**: missing-capability
**Area**: voice-pipeline
**Priority**: high

### Failure

El usuario indicó que el bot no hablaba en Discord después de añadir el servicio
Kokoro. La respuesta del LLM se publicaba exclusivamente por texto.

### Diagnosis

`VoiceTranscription._llm_loop` no llamaba a Kokoro y no existía ninguna ruta de
reproducción en Discord. Las pruebas anteriores verificaban WAV/servidor, no la
respuesta de voz del bot.

### Fix

Añadidos cliente HTTP, adaptador PCM y reproducción con callback, cola de voz,
comprobación de salud/voz/permisos en `/join` y cancelación al usar `/leave`.
Archivos: `kokoro_client.py`, `voice_transcription.py`, `bot.py`.

### Verification

30 pruebas automáticas pasan. Compilación y diff check correctos. El comprobador
`scripts/check_voice_pipeline.py` ejecutó los modelos reales de Whisper, llama y
Kokoro, y produjo 130 paquetes Opus de salida; el supervisor cerró con código 0.
La corrección está aplicada y verificada localmente. El estado se mantiene en
pending-verify porque no se ha conectado a Discord ni confirmado audio audible
en un canal real.

### Metadata

- Related Files: kokoro_client.py, voice_transcription.py, bot.py, docs/kokoro_pipeline_review.md
- Pattern-Key: voice.missing_tts_output_transport
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-10-14

## Registros verificados — 2026-10-15

Las rutas de la entrada anterior son históricas; los comandos actuales están
en README y docs/RUNBOOK.md. No se ha verificado una llamada audible en Discord.

- [HEAL-20261015-001](heals/HEAL-20261015-001.md): entrada única y migración.
  Pattern-Key: runtime.single_entry_migration. Status: verified.
- [HEAL-20261015-002](heals/HEAL-20261015-002.md): requisitos y entornos.
  Pattern-Key: dependencies.direct_requirements_validation. Status: verified.
- [HEAL-20261015-003](heals/HEAL-20261015-003.md): stdin heredado y cierre.
  Pattern-Key: processes.inherited_control_stdin. Status: verified.
- [HEAL-20261015-004](heals/HEAL-20261015-004.md): readiness en Windows.
  Pattern-Key: processes.readiness_windows_redirector. Status: verified.

## [HEAL-20261030-001] fairyweb-sandbox-network

**Logged**: 2026-10-30
**Status**: verified
**Trigger**: env-issue
**Area**: FairyWeb local server
**Priority**: low

### Failure
El sandbox no resolvió github.com durante la descarga de llama.cpp y rechazó los sockets locales al consultar `/health`.

### Diagnosis
La descarga oficial y la comprobación local funcionaron con acceso fuera del sandbox. El modelo requiere llama.cpp b11960 o posterior; la copia existente era b11675.

### Fix
Descargada la versión oficial b11960 en FairyWeb y ejecutado el servidor local fuera del sandbox.

### Verification
`/health` y `/` devolvieron HTTP 200. La prueba WebSocket envió voz PCM y recibió 341760 bytes de audio y texto generado.

### Metadata
- Pattern-Key: sandbox.local_network_denied
- Recurrence-Count: 3
- First-Seen / Last-Seen: 2026-10-30 / 2026-11-01

**2026-11-01 recurrence**: `setup.py --yes --only models` no resolvió el servidor dentro del sandbox. La misma orden fuera del sandbox descargó y verificó los tres GGUF mediante SHA-256.

**2026-10-31 recurrence**: El servidor de prueba WebSocket quedó bloqueado dentro del sandbox. Fuera de él aceptó un JPEG, lo entregó por ID y lo eliminó al cerrar la conexión.

## [HEAL-20261031-001] omni-python315-runtime

**Status**: verified
**Pattern-Key**: dependencies.discord_receiver_conflict; sandbox.asyncio_socket
**Trigger**: La `.venv` de Python 3.15 contenía `discord-ext-voice-recv` de otro fork. Las pruebas de asyncio con sockets quedaron bloqueadas dentro del sandbox.
**Diagnosis**: El receptor instalado no era el fork DAVE fijado por la repo. El bloqueo del sandbox no demostraba un fallo del modelo.
**Fix**: Se sustituyó el receptor por el fork DAVE fijado y se ejecutaron las pruebas de sockets y modelo fuera del sandbox. Setup detecta el conflicto antes de instalar.
**Verification**: `pip check`, comprobación de revisión, build 11960 y SHA-256 de ambos GGUF correctos. El modelo real respondió a audio y conservó contexto después de cancelar. Una prueba local codificó 128 frames Opus. Login y llamada real pendientes.
**Recurrence-Count**: 3

**2026-10-31 recurrence**: Una prueba del historial administrativo quedó bloqueada al crear el event loop dentro del sandbox. La misma prueba pasó fuera del sandbox: límite de eventos y rechazo de peticiones sin token. No acredita una sesión Discord real.

**2026-11-01 recurrence**: `python -m unittest discover -s checks -v` quedó bloqueado al crear el event loop dentro del sandbox. La misma orden pasó fuera del sandbox: ocho pruebas, sin errores. No acredita una llamada Discord ni inferencia real.

## [HEAL-20261101-001] Invalid vision smoke input

**Status**: verified
**Pattern-Key**: vision.invalid_smoke_image
**Trigger**: Una imagen diminuta inválida en la prueba de visión produjo una descripción inventada.
**Diagnosis**: La entrada de prueba no era un PNG válido, por lo que su respuesta no acreditaba visión.
**Fix**: Se repitió la prueba con un PNG válido de 64 × 64 píxeles y color conocido.
**Verification**: LFM3 identificó el color rojo mediante el adaptador real. No se evaluó la precisión con imágenes reales ni la validación integral de archivos.
**Recurrence-Count**: 1

## [HEAL-20261031-002] MiniCPM model download

**Status**: pending-verify
**Pattern-Key**: minicpm.huggingface_connection_reset
**Trigger**: La primera descarga de los GGUF terminó con WinError 10054; el archivo no se publicó parcialmente.
**Diagnosis**: El servidor respondió a HEAD con HTTP 200 y soporte de rangos; la causa del cierre remoto no está confirmada.
**Fix**: El instalador reanuda descargas parciales con curl y verifica tamaño y SHA-256 antes de publicar cada archivo.
**Verification**: Los diez componentes de MiniCPM se descargaron y verificaron con SHA-256, 8.872.297.088 bytes en total.

## [HEAL-20261031-003] Kokoro dependencies on Python 3.15

**Status**: abandoned
**Pattern-Key**: dependencies.kokoro_python315
**Trigger**: La instalación solicitada de Kokoro debe usar la única `.venv` de Python 3.15.
**Diagnosis**: `pip install --dry-run --only-binary=:all: kokoro==0.7.16` no encuentra una versión compatible de `misaki>=0.7.16`. La alternativa `kokoro-onnx` no encuentra una distribución compatible de `onnxruntime`.
**Fix**: Ninguno aplicado. Se conserva System.Speech y no se fuerzan dependencias incompatibles.
**Verification**: Ambas resoluciones se probaron con acceso a PyPI fuera del sandbox; fallaron por las dependencias indicadas. PyTorch ofrece una distribución para Python 3.15, lo cual no resuelve los otros requisitos.
**Recurrence-Count**: 1

## [HEAL-20261031-004] llama UI gzip

**Status**: verified
**Pattern-Key**: llama.ui_requires_gzip
**Trigger**: La comprobación HTTP de la interfaz devolvió 415.
**Diagnosis**: La interfaz incorporada requiere que el cliente anuncie soporte gzip; urllib no lo hace por defecto.
**Fix**: La prueba solicita `Accept-Encoding: gzip`, como un navegador compatible.
**Verification**: La interfaz respondió HTTP 200 con `Content-Encoding: gzip` en un puerto temporal; el servidor se cerró.
**Recurrence-Count**: 1

## [HEAL-20261031-006] Kokoro worker callback stalls with stdin reader thread

**Status**: verified
**Pattern-Key**: kokoro.callback_stdin_thread_stall
**Trigger**: A persistent worker using a concurrent stdin reader did not deliver audio during native generation.
**Diagnosis**: The callback did not progress until the control reader was awakened; the exact runtime interaction is unconfirmed.
**Fix**: Process one bounded text segment at a time in the worker. The supervisor discards the in-flight segment on cancellation, avoids submitting remaining segments and terminates the worker if draining exceeds ten seconds.
**Verification**: The real model produced three separate PCM fragments; cancellation delivered no stale chunks, the same worker generated another phrase and closed cleanly. Cancellation cannot stop native inference mid-segment.
**Recurrence-Count**: 1

## [HEAL-20261101-002] Cancelled startup ownership

**Status**: verified
**Pattern-Key**: processes.cancelled_startup_ownership
**Trigger**: Code review found that cancellation while `run()` awaited model readiness did not cancel or await its startup and quit tasks. A server result could remain unclaimed.
**Diagnosis**: Process variables were assigned only after readiness; the finalizer could see `None` while a child task still owned a process.
**Fix**: Track startup and quit tasks, cancel and await pending tasks, collect completed process results, and stop each owned process once.
**Verification**: Two tests in `checks/test_runner_shutdown.py` passed outside the sandbox. Cancellation during loading awaited cleanup and left no pending task. Cancellation after startup completed stopped its unclaimed process exactly once. These use test doubles, not actual model processes.
**Recurrence-Count**: 1

## [HEAL-20261101-003] Screen tool availability guidance

**Status**: verified
**Pattern-Key**: tools.screen_availability_guidance
**Trigger**: MiniCPM denied having screen access during two real synthetic voice requests despite a registered `view_screen` tool and a recent frame.
**Diagnosis**: The tool schema alone did not reliably communicate that the current user's screen was available. ASR transcribed the request correctly.
**Fix**: Add temporary system guidance when a fresh frame is available, explaining that screen questions require the registered tool. Restore instructions and tools after the voice turn.
**Verification**: With both real models, MiniCPM called `view_screen`, LFM3 analyzed the synthetic frame, MiniCPM answered its main color and LFM3 emitted 199680 PCM bytes. LFM3 also invented unrelated flag details; visual accuracy remains limited. No Discord or human listening was tested. Processes and auxiliaries were cleaned up.
**Recurrence-Count**: 1
# HEAL-20261108-001: Python blocked by sandbox

**Status**: verified
**Trigger**: environment permission error
**Area**: verification

The virtual environment's Python launcher could not access the base Python 3.15 executable inside the sandbox. Running `./.venv/Scripts/python.exe -m compileall -q fairy/desktop` with approved elevated execution completed successfully. This verifies syntax only.

**Pattern-Key**: env.python_base_access_denied
**Recurrence-Count**: 1
