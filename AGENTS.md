# Guía de trabajo para agentes

## Alcance

Lee README.md, ARCHITECTURE.md, docs/RUNBOOK.md y docs/VERIFICATION.md. Ejecuta comandos desde la raíz. `afairy` es la versión antigua; `bfairy` conserva la versión anterior a la implementación actual. Respeta ambas y los cambios pendientes del usuario. No restaures `scripts/`, `tests/`, `setup/` ni `tool/` sin petición nueva.

## Estructura actual

- `main.py`: inicio conjunto; `setup.py`: instalación y comprobaciones.
- `fairy/runner/`: servidor, readiness y cierre; `fairy/bot/`: Discord y comandos.
- `fairy/ai/`: MiniCPM y herramientas; `fairy/realtime/`: ASR, visión y TTS de LFM3; `fairy/voice/`: turnos por usuario; `fairy/audio/`: recepción, PCM y reproducción.
- `fairy/installation/`: instalador y verificación; `fairy/paths.py`: rutas; `fairy/prompts/`: prompt.
- `fairy/web/`: página informativa y fotogramas de pantalla temporales.
- `llama/`: binarios locales; `models/`: MiniCPM5, LFM3 y proyector. `docs/`: operación y evidencia; `.learnings/`: incidentes.

## Entorno e instalación

Usa Python 3.15 y una sola `.venv`, con `requirements.txt`. Prepara con `python setup.py --yes`. El instalador permite `--only all|environment|llama|models`, `--check` y `--verify-models`. Conserva el fork DAVE fijado y no instales simultáneamente el receptor upstream. No sobrescribas modelos o binarios existentes. La instalación automática de llama.cpp está orientada a Windows x64 y CUDA 13.4.

## Verificación

```powershell
./.venv/Scripts/python.exe -m compileall -q fairy main.py setup.py
./.venv/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe -m unittest discover -s checks -v
./.venv/Scripts/python.exe setup.py --check --verify-models
./.venv/Scripts/python.exe main.py --check
git diff --check
```

`compileall` comprueba sintaxis; `--check` no inicia sesión en Discord. Las pruebas unittest están en `checks/`; no hay configuración de Ruff, Black, mypy o pytest. Para cambios de audio o servicios prueba el modelo real con puertos temporales y limpia auxiliares. No atribuyas a una prueba offline login, DAVE ni audio audible. Ante bloqueo de sockets del sandbox verifica fuera de él; no lo ocultes ni amplíes timeouts para evitar comprobarlo.

## Contratos

La ruta usa MiniCPM5 para texto y herramientas y LFM3 para ASR, imágenes y TTS, mediante dos servidores llama.cpp en localhost. Espera `/health`, inicia la web local y Discord y cierra el bot y la web antes de ambos servidores. `q` o Ctrl+C solicitan cierre. Discord recibe y envía PCM16 estéreo a 48 kHz, con frames de 3840 bytes. La migración debe verificarse con modelos reales y una llamada Discord.

Conserva buffers por usuario, colas acotadas, cancelación y `call_soon_threadsafe` desde callbacks. Al interrumpir detén reproducción con `stop_playing()`, cancela generación y descarta audio obsoleto. No uses `VoiceRecvClient.stop()` para detener solo la salida. El contexto de voz es por usuario y se pierde al cerrar sesión; las intervenciones pendientes se descartan al interrumpir. La identidad usa ID y nombre de Discord, no biometría. MiniCPM puede pedir `view_screen` para un fotograma reciente del ID del usuario; LFM3 lo analiza. No se recibe Discord Go Live.

Mantén imports sin efectos de inicio, rutas centralizadas en `fairy/paths.py`, timeouts y `trust_env=False` para clientes locales. Usa cuatro espacios, tipos y dataclasses; identificadores, docstrings y mensajes de Discord en inglés. Sigue el estilo de `bfairy` salvo su `bot.py`, según la petición del usuario. No expongas tokens en logs.

## Entrega

No añadas `.env`, grabaciones, pesos, binarios, entornos ni auxiliares temporales. Actualiza documentación aplicable y registra incidentes reales en `.learnings/HEALS.md` sin borrar evidencia anterior. Indica verificaciones y límites. RVC y Kokoro no están integrados en la ruta actual.

La publicación de la web se decidirá después. No expongas el gateway local ni su panel sin diseñar y verificar autenticación, HTTPS y controles de acceso. Consulta `docs/WEB_LOCAL.md`.
