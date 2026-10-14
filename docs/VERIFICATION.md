# Verificación de la migración — 2026-10-15

## Resultados

| Comprobación | Resultado |
| --- | --- |
| Compilación de fairy/main/setup y diff check | Correctos |
| Regresiones previas adaptadas al límite de instalación nuevo | 41 comprobaciones pasan antes de eliminar tests |
| Controles finales temporales de arranque/cierre | 10 comprobaciones pasan |
| main.py --check | Código 0; sin login |
| setup.py --check | Código 0 |
| setup.py --check --verify-models | SHA-256 correcto de los tres modelos GGUF/GGML |
| pip check de ambos entornos | No broken requirements found |
| Modelos reales Whisper/llama/Kokoro/PCM/Opus | 147 paquetes Opus; supervisor código 0 |
| Arranque conjunto con servicios reales | Orden correcto |
| Discord construido offline | Comandos registrados y cierre confirmado por el intérprete real |
| Cierre conjunto | Hijos terminados y puertos temporales sin listener |
| CLI de Whisper mediante fairy.clients.whisper_cli --help | Entrada disponible tras eliminar tool |

Las 41 comprobaciones y los diez controles finales son ejecuciones separadas;
no constituyen 51 casos distintos. Los controles finales cubren orden, fallo
del bot, cancelación, modo check, token con PIDs diferentes, stdin aislado y
cierre ante q/fallo de login simulado.

## Límites

La prueba conjunta construye la aplicación Discord en un proceso offline sin
conectarse al gateway. Su cierre escribe una confirmación antes de salir, para
no confundir el fin del redirector del venv con el cierre del intérprete real.

No se comprobó login, DAVE ni escucha audible real. La parada por q se probó
con procesos reales; Ctrl+C desde una terminal de usuario no se ejercitó en
esa prueba. Los tests y auxiliares temporales de migración se eliminaron.

## Comandos mantenidos

```powershell
python -m compileall -q fairy main.py setup.py
git diff --check
python main.py --check
python setup.py --check --verify-models
./.venv/Scripts/python.exe -m pip check
./.venv-kokoro/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe -u -m fairy.diagnostics.voice_pipeline
```

## Incidencias corregidas

Entradas antiguas eliminadas; requisitos directos revisados; probes/servicios
con stdin aislado; readiness por token atómico y no EOF/PID; cierre por q y EOF
con límites. Se distinguieron los fallos de permisos del sandbox de los fallos
reales del proyecto. Los detalles están en `.learnings/HEALS.md`.
