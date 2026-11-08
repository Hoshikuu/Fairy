# Fairy

Fairy es un asistente local para Discord con Python 3.15 y dos servidores llama.cpp. MiniCPM5-2B genera texto, mantiene la conversación y solicita herramientas. LFM3-Omni-2B transcribe voz, analiza imágenes y sintetiza la respuesta final de MiniCPM.

## Preparación

Instala Python 3.15 y Git para Windows. Desde la raíz:

```powershell
python setup.py --yes
./.venv/Scripts/python.exe setup.py --check --verify-models
./.venv/Scripts/python.exe main.py --check
```

Setup prepara una sola `.venv`, el fork de recepción DAVE fijado, llama.cpp y los modelos GGUF en `models/`: MiniCPM5 Q4_K_M, LFM3 Q4_K_M, su proyector Q4_K_M y DSpark Q4_K_M. Verifica SHA-256 sin sobrescribir archivos existentes. La instalación automática de llama.cpp está orientada a Windows x64 y CUDA 13.4. No instales simultáneamente otro receptor `discord-ext-voice-recv`.

## Inicio y uso

Si falta DSpark Q4_K_M, setup descarga temporalmente el BF16 oficial, verifica su SHA-256 y genera el modelo cuantizado con `llama-quantize.exe`, sin sobrescribir archivos. La utilidad también acepta un archivo de origen proporcionado manualmente: `./.venv/Scripts/python.exe -m fairy.installation.quantize --source ruta/al/dspark.gguf --output models/otro-dspark.gguf`. MiniCPM utiliza DSpark para decodificación especulativa; `FAIRY_DRAFT_MODEL_PATH` permite elegir otro archivo compatible.

Define `TOKEN` en `.env`, habilita Message Content Intent y ejecuta:

```powershell
./.venv/Scripts/python.exe main.py
```

Fairy inicia LFM3 en `127.0.0.1:8080` y MiniCPM en `127.0.0.1:8082`, espera `/health`, inicia la web en `http://127.0.0.1:8081` y conecta Discord. `q` + Enter o Ctrl+C solicita el cierre. Usa `--port` y `--web-port` para cambiar los puertos de LFM3 y la web.

Usa `/ask` o una mención para texto, `/join` para conversar por voz y `/leave` para desconectar. Fairy anuncia que escucha, separa el audio por usuario, detecta el fin de cada intervención y permite interrumpir su respuesta. Solo responde a intervenciones; no genera comentarios espontáneos. `/reset` borra el contexto de texto del usuario en ese servidor o conversación privada. El contexto de voz es por usuario y se pierde al cerrar la sesión; no se guardan grabaciones por defecto.

Un mensaje admite hasta cuatro adjuntos JPEG, PNG o WebP de 8 MiB cada uno; `/ask` admite un adjunto. LFM3 analiza las imágenes según la pregunta y MiniCPM produce la respuesta. Para compartir pantalla, abre la web, introduce tu ID de Discord y elige una ventana o pantalla. MiniCPM dispone de la herramienta `view_screen` en texto y voz mientras exista un fotograma reciente del mismo ID. LFM3 analiza ese fotograma cuando MiniCPM lo solicita. La web es informativa y ofrece captura de pantalla; las conversaciones se realizan en Discord. Consulta [docs/WEB_LOCAL.md](docs/WEB_LOCAL.md).

## Configuración

`FAIRY_BRAIN_URL`, `FAIRY_BRAIN_MODEL_PATH`, `FAIRY_BRAIN_GPU_LAYERS`, `FAIRY_CONTEXT_SIZE` y `FAIRY_REASONING_MODE` configuran MiniCPM. `FAIRY_OMNI_MODEL_PATH`, `FAIRY_OMNI_PROJECTOR_PATH`, `FAIRY_OMNI_CONTEXT` y `FAIRY_OMNI_GPU_LAYERS` configuran LFM3. `FAIRY_OMNI_URL`, si se establece, debe usar localhost y el puerto `--port`. Los tres servicios requieren puertos distintos. Los valores predeterminados de `FAIRY_ASR_LANGUAGE`, `FAIRY_TTS_LANGUAGE` y `FAIRY_TTS_VOICE` son `English`, `English` y `female`. Consulta [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Verificación y límites

```powershell
./.venv/Scripts/python.exe -m compileall -q fairy main.py setup.py
./.venv/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe setup.py --check --verify-models
./.venv/Scripts/python.exe main.py --check
./.venv/Scripts/python.exe -m unittest discover -s checks -v
git diff --check
```

Ambos modelos ya respondieron simultáneamente en una prueba real; se comprobaron razonamiento y una llamada de herramienta de MiniCPM, además de visión, síntesis y transcripción de LFM3. La GPU registró 6023 de 8188 MiB ocupados, incluidos otros procesos, en esa medición puntual. Consulta [docs/VERIFICATION.md](docs/VERIFICATION.md) para distinguir la evidencia real de las pruebas simuladas. Faltan login y llamada Discord reales, escucha e interrupción audible, captura física de pantalla y estabilidad prolongada. Mantén los servicios locales: la web no está preparada para publicación. `afairy` y `bfairy` son versiones históricas conservadas.
