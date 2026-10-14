# Operación de Fairy

## Preparación y arranque

Con Python 3.12 operativo, desde la raíz:

```powershell
python setup.py --yes
python setup.py --check --verify-models
python main.py --check
python main.py
```

Define TOKEN en `.env` sin copiarlo a logs. Setup separa bot y TTS en `.venv`
y `.venv-kokoro`. Un fallo de acceso al Python Microsoft Store en un sandbox
no prueba que el intérprete haya sido eliminado; contrasta fuera de él.

El bot se inicia después de los tres servicios. Usa `q` + Enter para cierre
conjunto: cancela conexión y sesiones de Discord antes de detener los backends.

```powershell
python main.py --kokoro-port 9082 --kokoro-voice bf_emma
```

Las opciones se propagan al bot. En ejecución independiente, configura
LLAMA_URL, WHISPER_URL, KOKORO_URL y la voz correspondiente.

## Dependencias

```powershell
python setup.py --only bot
python setup.py --only kokoro
./.venv/Scripts/python.exe -m pip check
./.venv-kokoro/Scripts/python.exe -m pip check
```

No mezcles requisitos de ML con el entorno del bot. Se comprueban versiones
y la revisión Git del receptor DAVE, además de dependencias transitivas.
Los requisitos contienen dependencias directas, conservan OpenAI `<3`,
Kokoro/Misaki 0.9.4, Transformers `<5` y Hugging Face Hub `<1`.

Se contrastó metadata de [Kokoro 0.9.4](https://pypi.org/pypi/kokoro/0.9.4/json)
y [Transformers 4.57.6](https://pypi.org/pypi/transformers/4.57.6/json) con los
paquetes instalados. La aplicación utiliza `asyncio.timeout`, por lo que el
rango validado es Python 3.11–3.12; la referencia probada es 3.12.

## Binarios y modelos

```powershell
python setup.py --only models --yes --verify-models
python setup.py --only llama --force --yes
python setup.py --only whisper --backend cpu --force --yes
```

`--force` reinstala binarios existentes. No continúes utilizando un modelo
si falla su SHA-256. Si un puerto está ocupado, elige otro o detén el servicio
que reconoces; no cierres procesos ajenos por el número de puerto.

## Readiness y voz

El padre espera un JSON atómico con un token de su ejecución, no EOF ni un
PID aislado. Revisa logs de SERVICES, WHISPER, LLAMA y KOKORO. La espera inicial
es finita; `--startup-timeout` tiene 360 segundos por defecto.

Comprueba Conectar/Hablar, silencio del servidor y canal de voz normal.
Usa `/join`, habla en inglés y revisa transcripción/errores por texto.
`/leave` debe cancelar audio y desconectar.

## Diagnóstico local

```powershell
./.venv/Scripts/python.exe -u -m fairy.diagnostics.voice_pipeline
```

Arranca servicios temporales, ejecuta modelos reales y comprueba hasta Opus.
No inicia sesión en Discord. La llamada audible requiere una comprobación real.
