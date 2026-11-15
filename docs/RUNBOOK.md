# Operación de Fairy

## Inicio de la aplicación de escritorio

1. Instala Python 3.15, Git, Node.js con npm y un driver NVIDIA compatible con CUDA 13.4.
2. Desde la raíz del repositorio, prepara el entorno y modelos:
   ```powershell
   python setup.py --yes
   cd desktop
   npm install
   cd ..
   ```
3. Verifica los requisitos y archivos sin iniciar inferencia:
   ```powershell
   ./.venv/Scripts/python.exe setup.py --check --verify-models
   ./.venv/Scripts/python.exe main.py --check
   ```
4. Inicia la aplicación de escritorio:
   ```powershell
   ./.venv/Scripts/python.exe main.py
   ```
5. Espera a que la barra superior indique **Ready to chat** (con el indicador en verde). Para cerrar Fairy y terminar limpiamente ambos servidores de modelos, basta con cerrar la ventana de Electron.

---

## Puertos y variables de configuración

Fairy utiliza puertos locales independientes en `127.0.0.1`:

- **LFM3-Omni**: Puerto 8080 por defecto (`FAIRY_DESKTOP_OMNI_PORT` o `FAIRY_OMNI_URL`).
- **MiniCPM5**: Puerto 8082 por defecto (`FAIRY_BRAIN_URL`).
- **VTube Studio**: Puerto 8001 por defecto (`FAIRY_VTUBE_URL=ws://127.0.0.1:8001`).

Ambos servidores de modelos deben tener puertos distintos y libres antes de iniciar. Fairy comprueba los puertos al arrancar y rechaza listeners ajenos existentes.

### Optimización de memoria VRAM (valores predeterminados y `.env`)

La configuración por defecto está calculada para encajar con holgura en tarjetas de 8 GB de VRAM (como RTX 4060):

- `FAIRY_USE_DRAFT`: Por defecto `0` (desactivado). Desactiva el modelo auxiliar DSpark Q4_K_M para ahorrar memoria VRAM y CPU. Para reactivar decodificación especulativa, define `FAIRY_USE_DRAFT=1` en tu archivo `.env`. Requiere que `models/MiniCPM5-2.6B-DSpark-Q4_K_M.gguf` esté presente.
- `FAIRY_BRAIN_GPU_LAYERS`: Por defecto `20`. Carga 20 capas de MiniCPM en GPU y delega el resto a CPU. Si dispones de 12 GB o más de VRAM y deseas máxima velocidad, puedes redefinirlo a `FAIRY_BRAIN_GPU_LAYERS=99` en `.env`.
- `FAIRY_OMNI_GPU_LAYERS`: Por defecto `99`. Mantiene LFM3 completamente acelerado en GPU.
- `FAIRY_OMNI_CONTEXT`: Por defecto `2048` (reducido desde 4096 para acotar el uso de memoria de contexto).
- `FAIRY_CONTEXT_SIZE`: Por defecto `2048` (contexto de MiniCPM).
- **Flash Attention y cuantización de caché**: Ambos servidores arrancan con `-fa on` y claves/valores de caché cuantizados a 8 bits (`-ctk q8_0 -ctv q8_0`), reduciendo significativamente la memoria de atención.

---

## Uso de funciones y herramientas de escritorio

- **Interacción por voz y VAD**: Al pulsar **Record**, el micrófono graba y evalúa la energía sonora. La detección de voz y silencio (VAD) finaliza la grabación de manera automática tras detectar una pausa de habla (~1.8 s de silencio tras haber hablado) o al alcanzar el límite de 30 segundos. También puede detenerse manualmente pulsando **Stop recording**.
- **Síntesis por oraciones en streaming**: Las respuestas se sintetizan y transmiten en bloques de oraciones, de modo que el audio comienza a reproducirse sin esperar a que MiniCPM termine de redactar la respuesta completa.
- **Cancelación y reinicio**: **Stop response** interrumpe inmediatamente la inferencia y la reproducción de voz, descartando el turno pendiente sin corromper el historial. **New conversation** borra el historial de la sesión activa.
- **Control de escritorio (`Control: on/off`)**: El botón en la barra superior habilita las acciones del sistema. Cuando está en `on`, MiniCPM puede invocar:
  - `desktop_click`: Clic de ratón. Si se proporcionan `screen_width` y `screen_height` de la captura de pantalla, las coordenadas se escalan automáticamente a la resolución real del monitor.
  - `desktop_type`: Escritura de texto plano (hasta 200 caracteres) en la ventana enfocada vía `SendInput`.
  - `desktop_scroll`: Rueda del ratón (de -20 a +20 clics).
  - `desktop_key`: Pulsación de teclas como Enter, Escape, Tab, Espacio o flechas de dirección.
  - `media_control`: Teclas multimedia de Windows (reproducir/pausa, canción siguiente/anterior, subir/bajar volumen, silenciar).
- **Herramientas de asistencia del sistema**:
  - `get_current_time`: Consulta la hora, fecha y huso horario local.
  - `get_active_windows`: Consulta la ventana activa en primer plano y las ventanas visibles abiertas (hasta 15).
  - `get_system_stats`: Informa del espacio en disco, uso de memoria RAM física y uso de VRAM de la GPU.
  - `read_clipboard`: Lee el contenido actual en texto plano del portapapeles de Windows (hasta 2000 caracteres).
  - `remember_fact` y `recall_facts`: Recuerda y recupera notas y preferencias personales, persistidas en `.fairy_memory.json` (hasta 100 registros).
- **VTube Studio (`VTube: on/off`)**:
  - Requiere tener VTube Studio en ejecución con la opción «Start API» activada en su configuración (puerto 8001).
  - Al activar el botón por primera vez, VTube Studio mostrará una ventana pidiendo autorización para el plugin «Fairy». Tras aceptarla, el token se almacena en `.vtube_token`.
  - Durante el habla de Fairy, el audio se mide por RMS y se transmite al parámetro `MouthOpen` para sincronización labial en tiempo real.
  - Fairy puede solicitar expresiones faciales mediante la herramienta `set_expression` (`happy`, `smug`, `flustered`, `angry`, `surprised`, `sad`, `neutral`), disparando los hotkeys correspondientes en el modelo Live2D.

---

## Verificación completa del proyecto

Para verificar la integridad del código, tipos y pruebas unitarias:

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

---

## Operación histórica con Discord

Las instrucciones siguientes describen la versión anterior basada en Discord (no activa en el inicio habitual de escritorio):

1. Define `TOKEN` en `.env` y habilita Message Content Intent en el portal de desarrolladores de Discord.
2. Inicia `./.venv/Scripts/python.exe main.py` en modo legacy si se configuran los módulos correspondientes.
3. Entra en un canal de voz normal de Discord y escribe `/join`. Usa `/leave` para desconectar.
4. Para compartir pantalla, abre `http://127.0.0.1:8081`, introduce tu ID de Discord y comparte ventana o pantalla para que `view_screen` pueda analizarla.
