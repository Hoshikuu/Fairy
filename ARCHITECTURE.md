# Arquitectura de Fairy

## Organización

La raíz tiene dos entradas: `main.py` para ejecutar y `setup.py` para preparar
o comprobar. La implementación vive en `fairy/`.

| Responsabilidad | Módulos |
| --- | --- |
| Padre del arranque | `fairy/runtime/launcher.py` |
| Entradas de componentes | `fairy/start.py`, `fairy/bot.py` |
| Entornos y cierre | `fairy/runtime/environment.py`, `shutdown.py` |
| Configuración y prompt | `fairy/config/` |
| Clientes HTTP | `fairy/clients/` |
| Buffers, PCM y reproducción | `fairy/audio/` |
| Sesiones y trabajadores | `fairy/voice/` |
| Eventos/comandos/permisos | `fairy/discord_bot/` |
| Procesos y salud | `fairy/services/supervisor/` |
| Motor/API/esquemas TTS | `fairy/services/kokoro/` |
| Instalación | `fairy/installers/` |
| Diagnóstico | `fairy/diagnostics/` |

Las carpetas antiguas `scripts`, `tests`, `setup` y `tool` fueron eliminadas.
`llama/`, `whisper/` y `models/` contienen binarios, pesos y cachés.

## Arranque

1. El padre valida bot, configuración offline y requisitos de servicios.
2. Lanza `fairy.start` con el intérprete de `.venv-kokoro`.
3. El supervisor inicia Whisper, llama y Kokoro; drena logs y espera `/health`.
4. Publica un JSON atómico en un directorio temporal privado con un token por ejecución.
5. El padre valida el token y que el supervisor continúe activo.
6. Inicia `fairy.bot` con `.venv`, propagando URL/puertos y voz.
7. Vigila ambos procesos y cierra el conjunto ante una salida inesperada.

No se interpreta EOF como readiness. Tampoco se compara exclusivamente el PID:
el redirector de venv de Windows puede tener un PID diferente al intérprete.
Los archivos de readiness son temporales.

## Cierre

El padre interpreta `q` y señales. Envía `q` y cierra el pipe del bot. El bot
cancela su conexión antes de cerrar sesiones y recursos de Discord.
Después solicita `q` al supervisor, que detiene sus tres hijos.

El bot tiene hasta 20 segundos y el supervisor hasta 30 antes de la terminación
de respaldo. Las comprobaciones y servicios reciben `DEVNULL` en stdin para no
competir con el lector de control. Sólo instaladores interactivos heredan stdin.

## Voz

La sesión mantiene buffers e historiales por usuario y colas separadas de
transcripción, respuestas y voz. Se sintetizan fragmentos y se reproducen en orden.

- Recepción: PCM16 estéreo/48 kHz.
- Whisper: PCM16 mono/16 kHz, idioma `en`.
- Kokoro: WAV PCM16 mono/24 kHz.
- Discord: PCM16 estéreo/48 kHz, frames de 20 ms/3840 bytes.

`/leave` cancela síntesis/reproducción y descarta respuestas pendientes.
La transcripción conserva su cierre limitado a diez segundos.

## Setup

`setup.py` delega en `fairy.installers.orchestrator`, que puede preparar entornos
sin importar previamente paquetes pesados. El bot utiliza `requirements.txt` y
TTS utiliza `requirements-kokoro.txt`.

Se comprueban versiones declaradas, revisión Git DAVE, `pip check`, binarios,
tamaños de modelos y puertos. `--verify-models` comprueba SHA-256 y `--warmup`
carga Kokoro. Los binarios existentes se conservan salvo `--force`.

Rutas centralizadas en `fairy.config.paths`; `.env` se lee antes de construir
el bot. Importar módulos no inicia sesión ni descarga modelos.

## Comprobaciones

No existe suite permanente en `tests/`. Los comandos mantenidos están en
`AGENTS.md` y `README.md`; la evidencia está en `docs/VERIFICATION.md` y los
incidentes en `.learnings/HEALS.md`.

Se comprobaron modelos reales hasta Opus y arranque conjunto con inicialización
offline del bot. Login, DAVE y escucha audible real en Discord siguen pendientes.
