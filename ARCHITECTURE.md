# Arquitectura de Fairy

## Escritorio actual

`main.py` abre Electron desde `desktop/`. Electron inicia `fairy.desktop.bridge` mediante tuberías privadas; el puente inicia y supervisa los dos modelos y los cierra al terminar. La interfaz envía texto, PCM16 mono a 16 kHz y fotogramas JPEG temporales; recibe fragmentos PCM16 a 24 kHz y los reproduce. Una sola conversación mantiene su historial en memoria y la cancelación descarta el turno incompleto. `view_screen` analiza bajo demanda el último fotograma disponible mediante LFM3. Las herramientas de clic y teclas requieren la activación del control en la interfaz y notifican las acciones. No hay un gateway de escritorio HTTP.

La descripción siguiente documenta la arquitectura anterior de Discord y no corresponde al arranque actual.

`main.py` inicia dos procesos llama-server con MiniCPM y LFM3 más su proyector desde `models/`, espera `/health`, arranca la web local y conecta Discord. El cierre termina la web y el bot antes de detener los servidores propios. `setup.py` prepara la única `.venv`, llama.cpp y los modelos; `fairy/paths.py` centraliza las rutas.

MiniCPM carga también DSpark Q4_K_M como modelo auxiliar de decodificación especulativa. Setup verifica una descarga temporal del BF16 oficial y ejecuta la utilidad local de cuantización; conserva cualquier salida existente y elimina su descarga temporal.

```text
Discord texto ----------------------------------- MiniCPM -- respuesta
Discord imágenes -- LFM3 visión -- observaciones - MiniCPM -- respuesta
Discord PCM -- VAD por usuario -- LFM3 ASR -- MiniCPM -- LFM3 TTS -- Discord PCM
Web captura -- fotograma por ID -- view_screen -- LFM3 visión -- MiniCPM
```

MiniCPM recibe el prompt de personalidad y usa la plantilla nativa del GGUF. Las sesiones mantienen historial aislado y limitado; el razonamiento se separa de la respuesta final. MiniCPM decide las llamadas de herramientas, que pasan por un registro con validación de argumentos, timeout y límite de iteraciones. La transcripción ASR y el análisis visual se identifican como observaciones aportadas por LFM3. LFM3 comparte un límite de concurrencia entre ASR, visión y TTS.

El receptor traslada callbacks al event loop mediante colas acotadas, separa usuarios y detecta voz y silencio. El audio entrante se convierte a PCM mono de 16 kHz. La salida LFM3 a 24 kHz se adapta a PCM estéreo a 48 kHz con frames de 3840 bytes para Discord. Una interrupción detiene la reproducción, cancela la generación y descarta audio e intervenciones pendientes. Solo se responde a turnos recibidos; no existe generación espontánea tras inactividad.

La web contiene información y captura de pantalla. Recibe fotogramas temporales por ID de Discord. Cuando existe un fotograma reciente, las conversaciones de texto y voz del mismo usuario ofrecen a MiniCPM la herramienta `view_screen`; su ejecución solicita a LFM3 un análisis dirigido por la pregunta. MiniCPM utiliza esas observaciones para responder. Los fotogramas caducan y se eliminan al desconectar. Los IDs y nombres de Discord son identidad aportada por Discord, no biometría; el ID introducido en la página no autentica al usuario. No hay panel administrativo, historial web ni gateway de conversación en la web.

Se ha verificado inferencia simultánea con los dos modelos reales y herramientas con un handler simulado; falta una llamada Discord real y captura física de pantalla. La publicación requerirá diseñar y verificar autenticación, HTTPS y control de acceso. Consulta `docs/WEB_LOCAL.md` y `docs/VERIFICATION.md`.
