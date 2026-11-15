# Arquitectura de Fairy

## Aplicación de escritorio actual

`main.py` lanza Electron desde `desktop/`. Electron ejecuta `fairy.desktop.bridge` en un subproceso Python mediante tuberías privadas de entrada/salida estándar (protocolo JSON delimitado por saltos de línea). El puente inicia, supervisa y detiene los dos servidores locales llama.cpp, asegurando su cierre automático mediante un objeto de trabajo de Windows (Job Object) ante cualquier terminación inesperada.

```text
Electron (UI minimalista, VAD, audio)
   │ (JSON por stdin/stdout)
   ▼
fairy.desktop.bridge ──┬── DesktopSession ──┬── MiniCPM5 (puerto 8082, texto, herramientas, personalidad)
                       │                    └── LFM3-Omni (puerto 8080, ASR, visión, TTS por oraciones)
                       ├── VTubeClient ─────── VTube Studio (WebSocket local ws://127.0.0.1:8001)
                       ├── Herramientas ─────── Asistencia (tiempo, memoria, portapapeles, ventanas, stats)
                       └── Control Escritorio ── Win32 SendInput / mouse_event / SetCursorPos (opcional)
```

### Componentes principales

1. **Interfaz Electron (`desktop/`)**:
   - Diseño simplificado en una columna con barra superior de estado, mensajes de conversación, indicador de actividad de herramientas, campo de texto y botones de control.
   - Captura de audio de micrófono con detección automática de actividad vocal y silencio (VAD mediante RMS). Termina la intervención tras pausa de voz o 30 segundos.
   - Captura periódica de pantalla o ventana mediante diálogo selector y envío de fotogramas JPEG temporales.
   - Reproducción de fragmentos PCM16 a 24 kHz procedentes de la síntesis de voz.
   - Botones selectores para activar o desactivar el control de escritorio (`Control: on/off`) y la sincronización con VTube Studio (`VTube: on/off`).

2. **Puente y sesión (`fairy.desktop.bridge`, `fairy.desktop.session`)**:
   - Coordina el ciclo de vida de los modelos y las peticiones de conversación por texto o voz.
   - **Streaming de voz por oraciones**: `split_speech_sentences()` fragmenta la respuesta de MiniCPM en oraciones naturales (agrupando fragmentos menores a 20 caracteres) y solicita la síntesis de voz (`omni.speak`) de forma secuencial por oración, permitiendo iniciar la reproducción de audio casi de inmediato sin esperar al final del texto completo.
   - **Cancelación inmediata**: `Stop response` interrumpe la tarea asíncrona en curso, cancela la reproducción en la interfaz, resetea la apertura de boca en VTube Studio y restablece el historial al estado previo al turno cancelado.

3. **Optimización de memoria VRAM (`fairy.runner.dual`)**:
   - Ajustada por defecto para operar con margen en GPUs de 8 GB (como RTX 4060):
     - `FAIRY_USE_DRAFT=0`: Decodificación especulativa con DSpark desactivada por defecto (omite parámetros `-md`). Puede activarse con `FAIRY_USE_DRAFT=1`.
     - `FAIRY_BRAIN_GPU_LAYERS=20`: MiniCPM descarga 20 capas a GPU y delega el resto a CPU (ampliable a `99` en tarjetas con mayor VRAM).
     - `FAIRY_OMNI_GPU_LAYERS=99`: LFM3 descarga todas sus capas a GPU para acelerar ASR, visión y síntesis.
     - Contexto reducido a 2048 tokens en ambos modelos (`FAIRY_OMNI_CONTEXT=2048`, `FAIRY_CONTEXT_SIZE=2048`).
     - Flash Attention (`-fa on`) y caché KV cuantizada a 8 bits (`-ctk q8_0 -ctv q8_0`) en ambos servidores.

4. **Integración con VTube Studio (`fairy.desktop.vtube`)**:
   - Conexión WebSocket asíncrona contra `ws://127.0.0.1:8001`.
   - Protocolo oficial Public API v1.0: solicitud y verificación de token de plugin (`AuthenticationTokenRequest` / `AuthenticationRequest`), persistiendo la clave autorizada en `.vtube_token`.
   - **Sincronización labial (lip-sync)**: `compute_rms_mouth_open()` calcula el nivel RMS de cada bloque de audio PCM generado y lo inyecta en el parámetro `MouthOpen` (rango 0.0 a 1.0) mediante `InjectParameterDataRequest`.
   - **Expresiones faciales**: Herramienta `set_expression` para activar expresiones (`happy`, `smug`, `flustered`, `angry`, `surprised`, `sad`, `neutral`) invocando hotkeys configurados en el modelo Live2D.

5. **Herramientas del sistema y control de escritorio**:
   - **Herramientas de asistencia (`fairy.ai.tools`)**:
     - `get_current_time`: Fecha, hora, día de la semana y timestamp ISO.
     - `get_active_windows`: Título de la ventana activa en primer plano y lista de hasta 15 ventanas visibles abiertas (mediante Win32 `EnumWindows` y `GetWindowTextW`).
     - `get_system_stats`: Métricas de uso de disco, memoria física/paginada (`GlobalMemoryStatusEx`) y VRAM de GPU (vía `nvidia-smi` si está disponible).
     - `read_clipboard`: Lectura segura de texto plano del portapapeles de Windows (`CF_UNICODETEXT` hasta 2000 caracteres con bloqueo de memoria global).
     - `remember_fact` y `recall_facts`: Memoria local persistente guardada en `.fairy_memory.json` (hasta 100 hechos con claves y contenidos acotados).
   - **Control de escritorio (`fairy.desktop.control`)**:
     - Protegido por bandera de seguridad en la UI (`control_enabled`). Si está inactivo, las herramientas informan que el control está deshabilitado.
     - `desktop_click`: Clic en coordenadas físicas de pantalla. Admite parámetros opcionales `screen_width` y `screen_height` correspondientes a la captura de pantalla analizada; las coordenadas se escalan proporcionalmente a las dimensiones reales del monitor mediante `GetSystemMetrics`.
     - `desktop_type`: Envía texto plano (hasta 200 caracteres Unicode) a la ventana enfocada usando `SendInput` con estructuras `INPUT` de 40 bytes en x64.
     - `desktop_scroll`: Desplazamiento vertical de la rueda del ratón (`mouse_event` con delta con signo).
     - `desktop_key`: Teclas de navegación (`enter`, `escape`, `tab`, `space`, flechas, `backspace`).
     - `media_control`: Teclas de medios y volumen de Windows (`play_pause`, `next_track`, `prev_track`, `volume_up`, `volume_down`, `volume_mute`).

6. **Reglas de personalidad y salida hablada (`fairy/prompts/system.txt`, `fairy/ai/brain.py`)**:
   - Prompt en inglés que define una personalidad ingeniosa, directa y espontánea como amiga cercana, sin frases robóticas ni formalismos excesivos.
   - Filtro de voz estricto (`sanitize_for_speech`): elimina emojis, símbolos Kaomoji, asteriscos, corchetes, bloques de código y marcas Markdown, garantizando que el texto entregado a LFM3 TTS sea limpio y pronunciable en inglés estándar.

---

## Arquitectura histórica de Discord

La descripción siguiente documenta la arquitectura anterior de Discord y no corresponde al arranque actual.

`main.py` iniciaba dos procesos llama-server con MiniCPM y LFM3 más su proyector desde `models/`, esperaba `/health`, arrancaba la web local y conectaba Discord. El cierre terminaba la web y el bot antes de detener los servidores propios. `setup.py` preparaba la `.venv`, llama.cpp y los modelos; `fairy/paths.py` centralizaba las rutas.

MiniCPM cargaba también DSpark Q4_K_M como modelo auxiliar de decodificación especulativa. El receptor trasladaba callbacks al event loop mediante colas acotadas, separaba usuarios y detectaba voz y silencio. La salida LFM3 a 24 kHz se adaptaba a PCM estéreo a 48 kHz para Discord. La web local aportaba captura de pantalla por ID de Discord. No hay un gateway de conversación en la web ni servicios públicos.
