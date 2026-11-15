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

## Uso

Espera a que ambos modelos estén listos. Escribe y pulsa **Send**; o pulsa **Record voice**, habla y pulsa **Stop recording**. La grabación termina automáticamente tras 30 segundos. **Stop response** cancela la generación y detiene el audio pendiente. **New conversation** borra el contexto de la sesión.

Con **Share screen** elige una pantalla o ventana; Fairy recibe fotogramas mientras esté activa y puede analizarlos cuando le preguntes. **Stop sharing** elimina el fotograma. El análisis se realiza bajo demanda, no es vídeo continuo interpretado automáticamente.

**Desktop control: on** permite a Fairy hacer clics en coordenadas físicas del escritorio y pulsar teclas de navegación; la acción se muestra en la barra lateral. Desactívalo cuando no quieras permitir esas acciones. Esta primera versión no escribe texto, ejecuta comandos ni proporciona una máquina virtual o un sandbox de aplicaciones. Las coordenadas de la imagen reducida no necesariamente coinciden con las coordenadas físicas del escritorio: no se ha demostrado un control visual fiable.

La conversación y los fotogramas son temporales y se pierden al cerrar. El puente entre Electron y Python utiliza tuberías del proceso; los servidores de modelos escuchan en localhost. La antigua web de pantalla y los módulos de Discord no forman parte del arranque de escritorio. No publiques los servicios locales; consulta [docs/WEB_LOCAL.md](docs/WEB_LOCAL.md).

## Configuración y verificación

LFM3 usa por defecto el puerto 8080 (`FAIRY_DESKTOP_OMNI_PORT` y, si se configura, `FAIRY_OMNI_URL` deben coincidir); MiniCPM usa 8082 (`FAIRY_BRAIN_URL`). Ambos deben estar libres y ser distintos. `FAIRY_ASR_LANGUAGE`, `FAIRY_TTS_LANGUAGE` y `FAIRY_TTS_VOICE` conservan sus valores predeterminados `English`, `English` y `female`. Los modelos y la GPU se configuran con las variables descritas en [docs/RUNBOOK.md](docs/RUNBOOK.md).

```powershell
./.venv/Scripts/python.exe -m compileall -q fairy main.py setup.py
./.venv/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe -m unittest discover -s checks -v
./.venv/Scripts/python.exe setup.py --check --verify-models
./.venv/Scripts/python.exe main.py --check
git diff --check
```

Las comprobaciones automáticas no demuestran captura física, escucha audible ni control correcto de ventanas reales. Consulta [docs/VERIFICATION.md](docs/VERIFICATION.md) para el estado de las pruebas. `afairy` y `bfairy` se conservan como versiones históricas.
