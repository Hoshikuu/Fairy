# Verificación de Fairy con LFM3-Omni

## Aplicación de escritorio

Se ejecutaron 30 pruebas unittest, incluidas tres con clientes simulados para la sesión de escritorio, cancelación y validación de fotogramas. En puertos temporales, los dos modelos reales arrancaron a través del puente: MiniCPM produjo una respuesta y LFM3 generó 192000 bytes PCM; el puente terminó con código 0. En otra ejecución real, al terminar forzadamente el puente, el objeto de trabajo de Windows cerró ambos servidores y sus puertos. También se verificaron compilación, `pip check`, hashes de los tres modelos oficiales y sintaxis JavaScript. Electron abrió una ventana titulada Fairy y cargó ambos modelos, pero el servicio de inspección de ventanas no estaba disponible, por lo que no se verificaron la interfaz ni su cierre normal visualmente.

La evidencia histórica que sigue corresponde a otras rutas y no demuestra la aplicación Electron. Quedan pendientes micrófono físico, reproducción audible, interrupción en la ventana, captura real, control de escritorio y estabilidad prolongada.

## Modelos Q4 y DSpark

Se verificaron los SHA-256 de MiniCPM Q4, LFM3 Q4, su proyector Q4 y el DSpark BF16 oficial. llama.cpp b11960 cuantizó DSpark a Q4_K_M (180,22 MiB de tensores). En servidores temporales separados, MiniCPM con DSpark respondió a una petición de texto y notificó 49 tokens propuestos y 14 aceptados; LFM3 Q4 con su proyector respondió a una petición de texto. Estas pruebas no verifican su funcionamiento simultáneo, ASR, TTS, visión ni Discord. El BF16 se eliminó después; setup verifica su hash al descargarlo temporalmente. El archivo cuantizado generado localmente no tiene un hash oficial conocido y `--verify-models` no comprueba su integridad criptográfica.

## Limpieza de la pipeline principal

Tras reducir la web a información y pantalla compartida, pasaron 27 pruebas unittest. Incluyen herramientas de pantalla, separación y descarte de audio por usuario, interrupción, rutas web retiradas, rechazo de orígenes ajenos y limpieza de fotogramas al cerrar WebSocket o aplicación. Las pruebas de cancelación de arranque usan procesos simulados. También pasaron compilación, comprobación de JavaScript, `pip check`, verificación SHA-256 de los tres modelos, `main.py --check` y `git diff --check`.

No se ha probado una captura física de pantalla desde el navegador ni una llamada Discord real. Las pruebas locales de transporte y los resultados del modelo con entradas sintéticas no sustituyen esas comprobaciones.

## Pantalla compartida en la pipeline dual

Una prueba sintética con ambos servidores llama.cpp reales generó una petición hablada mediante LFM3 TTS y la transcribió con LFM3 ASR. MiniCPM solicitó `view_screen` con una pregunta dirigida; el handler analizó un JPEG rojo de 64 × 64 mediante LFM3, y MiniCPM respondió que el color principal era rojo. La respuesta produjo 199680 bytes PCM. Se cerraron ambos procesos temporales y se eliminaron los auxiliares. No hubo navegador compartiendo una pantalla física, llamada Discord ni escucha humana.

La primera prueba solo describía la herramienta en su esquema y MiniCPM negó tener acceso a pantalla en vez de usarla. Una guía temporal de disponibilidad y uso de `view_screen` permitió completar la cadena. LFM3 acertó el color pero inventó detalles de una bandera y una cruz sobre el JPEG uniforme: esta prueba acredita el enrutamiento y no la precisión visual general. Las pruebas simuladas comprueban caducidad del frame, pregunta dirigida, registro temporal de herramientas y limpieza de frames y sockets al cerrar la web.

## Dos servidores llama.cpp

MiniCPM5 Q4_K_M y LFM3 Q8 con proyector se ejecutaron simultáneamente mediante llama.cpp en puertos temporales. Ambos respondieron a `/health`, también tras limitar CORS a localhost, y se cerraron sus procesos al terminar. La GPU registró 6023 de 8188 MiB ocupados en ese momento, incluidos otros procesos; no es una medida aislada ni garantiza margen para cargas prolongadas.

MiniCPM respondió correctamente a una suma con `enable_thinking` desactivado y activado. En esa prueba `reasoning_content` estuvo vacío en el primer caso y poblado en el segundo. Una llamada de prueba a `get_weather` pasó por el registro de herramientas, ejecutó un handler simulado y produjo una respuesta final con su resultado. LFM3 identificó un PNG rojo, produjo 99840 bytes PCM y transcribió ese audio como «Hello, my name is Fairy.». No hubo escucha humana ni llamada Discord; estas pruebas no acreditan estabilidad ni precisión general.

## Arquitectura dual experimental

En una inspección anterior se encontraron pesos LFM3 Q8 en `FairyWeb/` (1.846.240.768 bytes) y su proyector Q8 (506.842.528 bytes). Una consulta de `nvidia-smi` mostró una RTX 4060 con 8188 MiB totales y 980 MiB ocupados en ese momento; esa cifra no mide la carga de ambos modelos. Esta inspección no verificó MiniCPM mediante el servidor llama.cpp actual.

El modo dual, la transcripción, la síntesis exacta, el razonamiento nativo y el flujo completo de Discord requieren pruebas específicas con los servicios y modelos reales. La evidencia histórica posterior de LFM3 corresponde a una implementación anterior y no demuestra el funcionamiento de la nueva integración dual.

La nueva interfaz LFM3 se probó fuera del sandbox con llama.cpp b11960, Q8 y proyector en un puerto temporal. Identificó un PNG rojo de 64 × 64; la síntesis de «Hello, my name is Fairy.» produjo 107520 bytes PCM a 24 kHz, y ASR sobre ese audio devolvió la misma frase. No hubo escucha humana, llamada Discord ni MiniCPM. Una imagen inicial inválida produjo una respuesta inventada; la prueba de visión válida se repitió con un PNG correcto. El proceso auxiliar se cerró al terminar.

En una ejecución anterior, ocho pruebas de `./.venv/Scripts/python.exe -m unittest discover -s checks -v` pasaron fuera del sandbox, con servicios simulados. No acreditan la integración actual con MiniCPM mediante llama.cpp ni inferencia real. La compilación, `pip check`, `setup.py --check --verify-models`, `main.py --check` y `git diff --check` también pasaron para la configuración anterior.

Para una prueba manual: ejecuta `python setup.py --yes`, `main.py --check` y después `main.py`. Comprueba `/ask`, una imagen con una pregunta, `/join`, voz de dos usuarios, interrupción y `/leave`. Confirma por escucha que la síntesis reproduce el texto final, y mide latencia y VRAM con ambos modelos cargados. No se ha realizado esta lista completa.

## Evidencia histórica de implementaciones anteriores

Las siguientes pruebas describen versiones anteriores, no la ruta dual actual. Se conservan como registro y no acreditan el funcionamiento actual.

## Kokoro con sherpa-onnx

La normalización de los ejemplos Lenovo, LOQ, 825, 62€, 144Hz, 16GB, RTX y 5050 produjo 455424 bytes PCM sin avisos OOV en una prueba con Kokoro real. Los nombres fuera del léxico se deletrean y los emojis se omiten. Gemma y Kokoro reales entregaron dos fragmentos PCM durante una petición en streaming; una prueba simulada comprobó la salida antes de terminar el texto y la cancelación sin guardar el turno. No hubo llamada Discord.

La herramienta `view_screen` con audio real sintetizado se activó ante «Can you see my screen?» y no ante un saludo o una pregunta sobre la palabra screen. No se activó ante «Look at the window I am sharing»: persisten falsos negativos y no se ha demostrado una mejora estadística.

En Python 3.15, sherpa-onnx 2.0.1 generó PCM16 mono a 24 kHz con Kokoro en CPU. En una prueba del proceso persistente, la carga inicial tardó 1,51 s y tres fragmentos llegaron a los 2,31, 3,18 y 3,89 s desde el inicio de la petición. La versión 2.0 necesita el léxico inglés; las palabras desconocidas pueden fallar. Falta probar reproducción e interrupción audible en Discord.

## Migración a Gemma

En la actualización de pantalla, una prueba local con audio sintético y JPEG rojo hizo que Gemma describiera el color; una frase sin petición de pantalla fue clasificada como negativa. La prueba produjo PCM, sin llamada Discord. La interfaz de llama.cpp respondió HTTP 200 con soporte gzip en un puerto temporal. Un WebSocket de prueba aceptó un JPEG, lo hizo disponible por ID y lo eliminó al desconectar. El panel rechazó el acceso sin token y se comprobó el límite de su historial. Las pruebas de sockets se ejecutaron fuera del sandbox.

Gemma Q4_K_M, proyector F16 y draft Q4_K_M se descargaron y verificaron con SHA-256. El servidor b11960 cargó el modelo y el draft y respondió a una petición de texto. En una prueba local con voz sintetizada de entrada devolvió texto y Windows System.Speech generó 204634 bytes PCM; la respuesta solicitó aclaración, por lo que la comprensión del audio no queda acreditada. No se ha probado una llamada Discord ni micrófono o pantalla reales en la web.

## Alcance de las pruebas

El modelo real LFM3-Omni Q8 y su proyector se iniciaron con llama.cpp b11960 en un puerto temporal. Un audio sintetizado se envió por WebSocket y el modelo devolvió texto y PCM a 24 kHz. La siguiente pregunta recuperó el contexto. Tras cancelar otra respuesta, el turno posterior respondió con el nombre de la primera intervención.

Una prueba local alimentó el receptor con PCM de Discord simulado y llevó la respuesta real hasta codificación Opus: 128 frames. No hubo conexión a Discord. La interrupción de reproducción y la reutilización de sesión también se comprobaron con un cliente simulado.

El arranque conjunto se comprobó con el servidor real y un bot simulado: el bot se creó después de readiness y el servidor se detuvo cuando el bot terminó inesperadamente.

El instalador verificó SHA-256 de los dos GGUF existentes y build 11960. Se comprobó el rechazo de archivos ZIP con rutas inseguras y el conflicto de receptores. No se ha probado la descarga completa en una instalación vacía.

La visión se probó con un PNG rojo sintético y el servidor local; el modelo identificó el color. Pruebas simuladas comprobaron aislamiento por usuario y contexto visual. Las condiciones de proactividad, interrupción y cierre se probaron con Discord simulado; el modelo real generó PCM ante un mensaje proactivo. La redacción final de esa instrucción se ajustó después y aún no se ha probado con el modelo real.

## Límites

No se han probado login, DAVE, audio audible en una llamada real, cortes con micrófono físico, varios usuarios concurrentes ni estabilidad prolongada. La precisión del modelo y la detección de silencio necesitan evaluación con voces reales. El contexto después de una desconexión no se conserva.
