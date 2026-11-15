# Fairy

Fairy es un asistente local con una aplicación de escritorio Electron y dos servidores llama.cpp. MiniCPM5 mantiene la conversación y solicita herramientas; LFM3 transcribe voz, analiza imágenes y sintetiza la respuesta. La aplicación no necesita iniciar sesión en Discord.

## Preparación en Windows

Instala Python 3.15, Git y Node.js con npm. Desde la raíz de este repositorio:

```powershell
python setup.py --yes
cd desktop
npm install
cd ..
./.venv/Scripts/python.exe main.py --check
./.venv/Scripts/python.exe main.py
```

Si Node está instalado en `C:\Program Files\nodejs` pero no está en el PATH, abre una nueva terminal después de instalarlo o añade esa carpeta al PATH. Según la versión de npm, puede ser necesario aprobar el script de instalación de Electron cuando npm lo indique. `setup.py` conserva las dependencias fijadas del receptor DAVE de la versión anterior; la aplicación de escritorio no las usa. Los modelos y binarios existentes no se sobrescriben.

## Uso e interfaz

La interfaz de escritorio presenta un diseño simplificado en una sola columna con controles directos e indicador de actividad:

- **Conversación y voz**: Escribe y pulsa **Send** (o pulsa Enter); o pulsa **Record** para hablar. La captura de voz cuenta con detección automática de silencio (VAD), terminando el turno tras una pausa natural de voz o tras el límite máximo de 30 segundos. También es posible pulsar **Stop recording** manualmente. **Stop response** cancela la generación en curso y el audio restante. **New conversation** reinicia el contexto del modelo.
- **Síntesis por oraciones**: La respuesta hablada se transmite en streaming dividida por oraciones (`split_speech_sentences`), reduciendo la latencia de inicio de reproducción.
- **Share screen**: Permite seleccionar una pantalla o ventana; Fairy recibe fotogramas periódicos y puede analizarlos bajo demanda mediante LFM3 (`view_screen`). **Stop sharing** detiene el envío y borra el fotograma activo.
- **Control: on/off**: Habilita o deshabilita las acciones de escritorio de Fairy. Cuando está activo (`Control: on`), MiniCPM puede realizar clics absolutos con escalado de resolución (`desktop_click` con `screen_width` y `screen_height`), escribir texto corto (`desktop_type`, hasta 200 caracteres mediante SendInput), pulsar teclas de navegación (`desktop_key`), desplazarse verticalmente (`desktop_scroll`) y controlar reproducción o volumen multimedia (`media_control`). Por seguridad, estas acciones se rechazan si el control está desactivado.
- **VTube: on/off**: Conecta o desconecta la integración con VTube Studio a través de WebSocket local (`ws://127.0.0.1:8001`). Al activarse por primera vez, VTube Studio muestra un cuadro de diálogo para autorizar el plugin «Fairy»; el token concedido se guarda localmente en `.vtube_token`. Durante la reproducción de voz, Fairy transmite sincronización labial inyectando el valor RMS del audio en el parámetro `MouthOpen`, y puede activar expresiones faciales del modelo Live2D (`set_expression` con gestos como happy, smug, flustered, angry, surprised, sad o neutral).
- **Herramientas locales de asistencia**: MiniCPM dispone de herramientas del sistema sin requerir control de escritorio: fecha y hora local (`get_current_time`), títulos de ventanas activas y en primer plano (`get_active_windows`), uso de RAM, disco y VRAM de GPU (`get_system_stats`), lectura de texto del portapapeles (`read_clipboard`), y almacenamiento persistente de preferencias o datos en `.fairy_memory.json` (`remember_fact` y `recall_facts`).

## Optimización de VRAM y configuración

El sistema arranca por defecto con una configuración optimizada para tarjetas con 8 GB de VRAM:

- `FAIRY_USE_DRAFT=0`: Desactiva por defecto el modelo de decodificación especulativa (DSpark) para ahorrar memoria. Puede reactivarse definiendo `FAIRY_USE_DRAFT=1` en `.env`.
- `FAIRY_BRAIN_GPU_LAYERS=20`: Descarga 20 capas de MiniCPM a la GPU y el resto a CPU. Para descargar el modelo completo a GPU en tarjetas con mayor memoria, define `FAIRY_BRAIN_GPU_LAYERS=99`.
- `FAIRY_OMNI_CONTEXT=2048` y `FAIRY_CONTEXT_SIZE=2048`: Ventana de contexto reducida a 2048 tokens.
- `-fa on`: Flash Attention activado en ambos servidores llama.cpp.
- `-ctk q8_0 -ctv q8_0`: Cuantización de 8 bits para las claves y valores de la caché KV en ambos servidores.

LFM3 usa por defecto el puerto 8080 (`FAIRY_DESKTOP_OMNI_PORT` o `FAIRY_OMNI_URL`); MiniCPM usa el puerto 8082 (`FAIRY_BRAIN_URL`). Ambos deben ser distintos y estar libres. Consulta [docs/RUNBOOK.md](docs/RUNBOOK.md) para más detalles.

## Verificación

```powershell
./.venv/Scripts/python.exe -m compileall -q fairy main.py setup.py checks
./.venv/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe -m unittest discover -s checks -v
./.venv/Scripts/python.exe setup.py --check --verify-models
./.venv/Scripts/python.exe main.py --check
node --check desktop/main.js
node --check desktop/preload.js
node --check desktop/renderer.js
git diff --check
```

Las comprobaciones automáticas prueban lógica, esquemas, APIs simuladas y arranque sin sustituir la prueba física con micrófono, altavoces, ventanas reales o VTube Studio activo. Consulta [docs/VERIFICATION.md](docs/VERIFICATION.md).
