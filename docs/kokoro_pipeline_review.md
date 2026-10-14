# Revisión de la pipeline de voz — 2026-10-14

## Fallo observado y causa

El síntoma indicado fue que Fairy no hablaba en Discord. El servicio Kokoro
estaba implementado, pero el bot no tenía ningún cliente de síntesis ni ninguna
llamada a `voice_client.play`. `VoiceTranscription._llm_loop` enviaba la respuesta
de llama exclusivamente a `text_channel.send`. Arrancar Kokoro no podía producir
voz en el canal porque faltaba su conexión con el bot.

Las pruebas anteriores de generación de WAV y arranque de servicios verificaban
el servidor, pero no cubrían la entrega de una respuesta de voz del bot.

## Revisión por etapa

| Etapa | Resultado de la revisión | Acción |
| --- | --- | --- |
| Instalación | Kokoro tiene entorno separado, dependencias y caché de modelos | Se mantiene el instalador existente |
| Supervisor | Arranca Whisper, llama y Kokoro; espera `/health`; cierra los hijos | Verificado con los tres servicios reales |
| Modelo/G2P | Voz inglesa, modelo persistente, calentamiento antes de aceptar peticiones | Síntesis real verificada |
| API TTS | POST `/v1/audio/speech`, texto de hasta 4000 caracteres, voz configurada y WAV PCM16 mono/24 kHz | Contrato y errores verificados |
| Bot → API | No existía | Añadido `kokoro_client.synthesize_wav`, asíncrono, con timeout y límite de descarga |
| Formato Discord | No existía conversión de salida | Añadida conversión a PCM16 estéreo/48 kHz y frames de 20 ms/3840 bytes |
| Reproducción | No existía | Añadido `voice_client.play` y espera de su callback desde el hilo de audio |
| Respuestas largas | El límite de la API podía impedir reproducir respuestas largas | Se dividen en fragmentos de hasta 1000 caracteres |
| Concurrencia | Sólo había colas para Whisper y llama | Añadida cola de ocho respuestas, reproducción secuencial, escucha independiente |
| Configuración | El bot no conocía la URL ni la voz del TTS | Añadidas variables `KOKORO_URL`, `KOKORO_VOICE` opcional y `KOKORO_SPEED` |
| Permisos | `/join` comprobaba Conectar, pero no Hablar | Ahora comprueba Hablar, silencio del servidor y canales de voz normales |
| Disponibilidad | No se comprobaba Kokoro en `/join` | Se consulta `/health` y se detecta una voz configurada diferente |
| Cancelación | No había reproducción que cancelar | `/leave` cancela síntesis/reproducción y descarta la cola de voz inmediatamente |
| Errores | No había diagnóstico de TTS en el bot | Se informa por texto y consola; un fallo no mata el trabajador de voz |

La nueva ruta es:

```text
Audio por usuario → Whisper → llama → cola de respuestas
                                   → Kokoro HTTP → WAV 24 kHz mono
                                   → PCM 48 kHz estéreo → Opus → Discord
```

`/ask` y las menciones continúan respondiendo por texto. Las respuestas de las
conversaciones iniciadas con `/join` se reproducen por voz. Se mantienen las
transcripciones en el canal de texto.

## Evidencia de verificación

- Compilación Python y `git diff --check`: correctos.
- 30 pruebas automáticas pasan: servidor, cliente HTTP, formato PCM, reproducción,
  permisos, historiales, errores y cancelación.
- `scripts/check_voice_pipeline.py` arrancó los tres servicios en puertos
  temporales. Se sintetizó una frase de entrada, se alimentó el receptor del bot,
  Whisper la transcribió y llama respondió. Kokoro sintetizó esa respuesta y el
  adaptador produjo **130 paquetes Opus** con el codificador real de discord.py.
- El supervisor terminó con código 0 tras recibir `q`.
- La prueba local no se conecta a Discord. Comprueba el trayecto hasta la
  codificación; no comprueba recepción de paquetes, DAVE, permisos efectivos,
  temporización de envío o escucha audible en un canal real.

## Comprobación final en Discord

1. Arranca los servicios y espera a que los tres estén listos.
2. Reinicia el bot para cargar el código actualizado.
3. Entra en un canal de voz normal, concede Conectar/Hablar y usa `/join`.
4. Di una frase en inglés. Debe aparecer la transcripción y oírse la respuesta.
5. Usa `/leave` durante una respuesta: debe detener el audio y desconectarse.

Si Kokoro escucha en otro puerto, `KOKORO_URL` debe apuntar a ese puerto. Si
defines `KOKORO_VOICE`, debe coincidir con `--kokoro-voice`; si la omites, el
cliente utiliza la voz del servicio.

## Revisión de calidad posterior

Se revisaron los archivos modificados tras la verificación: aislamiento de
recepción/reproducción, límites de descarga y colas, callback entre hilos,
cancelación, limpieza de fuentes y parámetros de HTTP. Se eliminó un import
sin uso del comprobador. No se introdujeron nuevas dependencias de ejecución.
La comprobación audible en Discord queda pendiente; las pruebas locales no la
sustituyen.
