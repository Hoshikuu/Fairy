# Guía de trabajo para agentes

## Alcance y estructura

Fairy es un bot con Whisper, llama.cpp y Kokoro locales. Esta guía se aplica a
toda la repo. Lee README, arquitectura y `docs/RUNBOOK.md`. Ejecuta comandos
desde la raíz, salvo indicación contraria.

```text
main.py                    Entrada conjunta
setup.py                   Instalación y comprobaciones
fairy/start.py             Entrada de los tres servicios
fairy/bot.py               Entrada y ciclo de vida del bot
fairy/runtime/             Orquestación, entornos, readiness y cierre
fairy/config/              Rutas, entorno y prompt
fairy/clients/             HTTP
fairy/audio/               Buffers, PCM y reproducción
fairy/voice/               Sesiones y trabajadores
fairy/discord_bot/         Eventos, comandos y permisos
fairy/services/            Supervisor y API/motor TTS
fairy/installers/          Instaladores y utilidades comunes
fairy/diagnostics/         Comprobación real de la pipeline
docs/                      Operación y evidencia
.learnings/                HEAL
```

El usuario eliminó `scripts/`, `tests/`, `setup/` y `tool/`. No restaures esos
directorios/adaptadores sin una petición nueva. `setup.py` sigue siendo una entrada.

## Entornos

- Referencia: Python 3.12; la aplicación valida 3.11–3.12 por `asyncio.timeout`
  y el límite de Python de Kokoro 0.9.4.
- `.venv` usa `requirements.txt`; `.venv-kokoro` usa `requirements-kokoro.txt`.
  No mezcles ambos entornos.
- Prepara con `python setup.py --yes`, usando un Python operativo.
  `--only bot` y `--only kokoro` seleccionan componentes.
- Mantén requisitos directos, rangos compatibles y SHA del fork DAVE.
  No instales simultáneamente el receptor upstream original.
- Un Python de Microsoft Store puede fallar dentro del sandbox y funcionar
  fuera. No diagnostiques un intérprete eliminado sólo por ese fallo.

## Compilación y validación

No hay build nativo ni empaquetado de la aplicación configurados:

```powershell
python -m compileall -q fairy main.py setup.py
git diff --check
python main.py --check
python setup.py --check
```

`compileall` sólo comprueba sintaxis. `main.py --check` valida configuración
(incluido TOKEN), paquetes, Opus, binarios y puertos, sin login.
No hay configuración de Ruff, Black, mypy o pytest; no inventes comandos de lint.

## Tests y comprobaciones actuales

No existe una suite permanente en `tests/`. No documentes discovery de esa
carpeta como un comando actual. Usa:

```powershell
./.venv/Scripts/python.exe -m pip check
./.venv-kokoro/Scripts/python.exe -m pip check
python setup.py --check --verify-models
./.venv/Scripts/python.exe -u -m fairy.diagnostics.voice_pipeline
```

El diagnóstico necesita ambos entornos, binarios y modelos. Usa puertos
temporales y verifica hasta Opus; no acredita login, DAVE ni audio audible.
Ejecuta modelos para cambios de servicios/audio, no para ediciones documentales.
Si necesitas regresiones nuevas, utiliza comprobaciones temporales, registra
resultados y elimina auxiliares. No restaures la carpeta de tests por rutina.
Ante bloqueos de permisos/sockets del sandbox, solicita ejecución fuera de él;
no ocultes fallos ni amplíes timeouts para evitar comprobarlos.

## Ejecución

```powershell
python main.py
```

El padre espera el token de readiness del supervisor antes de lanzar Discord.
`q` o `Ctrl+C` solicita cierre conjunto. Ante un fallo, debe detener el resto.
Entradas independientes: `python -m fairy.start`, `python -m fairy.bot` y
`python -m fairy.services.kokoro`, cada una con su entorno correspondiente.
Puertos por defecto: 8080/8081/8082.

## Convenciones

- Cuatro espacios; `snake_case`, `PascalCase` y constantes `UPPER_SNAKE_CASE`.
- Identificadores/docstrings principalmente en inglés; mensajes de Discord
  principalmente en español. Respeta el estilo del módulo.
- Conserva tipos y dataclasses; tipa interfaces nuevas.
- Importa desde `fairy` o relativamente dentro del paquete. Mantén entradas pequeñas.
- Centraliza rutas con `pathlib.Path` en `fairy/config/paths.py`.
  No añadas rutas de máquina ni dependencia del directorio de trabajo.
- Importar módulos no debe iniciar servicios, login ni descargas.
- HTTP asíncrono en el bot, timeouts explícitos y `trust_env=False` en HTTPX local.
- Conserva buffers por usuario, locks, colas acotadas y cancelación.
  Los callbacks notifican al loop mediante `call_soon_threadsafe`.
- Contratos: Whisper PCM16 mono/16 kHz; Kokoro WAV PCM16 mono/24 kHz;
  Discord PCM16 estéreo/48 kHz y frames de 3840 bytes. Transcripción `en`.
- Usa `stop_playing()` para detener sólo envío; `VoiceRecvClient.stop()` también
  detiene recepción.
- Readiness usa token único y JSON atómico; EOF/PIDs aislados no son suficientes
  con los redirectores de venv de Windows.
- Probes/servicios no heredan el pipe de control de `q`; instaladores interactivos sí.
- Mantén cierre limitado, conexión cancelada antes de liberar Discord y bot
  detenido antes de sus backends. No expongas tokens en logs.

## Entrega

Respeta cambios pendientes del usuario. No añadas `.env`, grabaciones, pesos,
binarios, entornos ni auxiliares temporales. Después de verificar cambios,
registra incidentes en `.learnings/HEALS.md` y actualiza documentación aplicable.
Declara lo comprobado y los límites; no presentes una prueba offline como llamada real.
