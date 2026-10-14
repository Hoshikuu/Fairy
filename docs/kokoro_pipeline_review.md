# Pipeline de Kokoro — estado actualizado

El servidor inicial no estaba conectado a la reproducción del bot. Ese tramo
se añadió y ahora se organiza en clientes HTTP, audio, trabajadores de voz y
motor/API TTS dentro de `fairy/`.

- `fairy/clients/kokoro.py`: salud y síntesis.
- `fairy/audio/pcm.py`, `playback.py`, `text.py`: formato, reproducción y fragmentación.
- `fairy/voice/speech.py`: síntesis/reproducción secuencial.
- `fairy/voice/session.py`: colas y ciclo de vida.
- `fairy/services/kokoro/`: motor persistente, API y esquemas.
- `fairy/runtime/launcher.py`: espera de servicios e inicio del bot.

Kokoro precarga modelo/voz y sintetiza antes de estar listo. Mantiene límites
de texto/velocidad y una síntesis con dos peticiones esperando.
Su WAV mono/24 kHz se convierte a PCM16 estéreo/48 kHz; los frames tienen 3840 bytes.
La recepción sigue activa mientras habla. `/leave` cancela síntesis y reproducción.

El arranque normal es `python main.py`. La revisión del 2026-10-15 verificó
modelos reales hasta 147 paquetes Opus y cierre del supervisor con código 0.
El arranque conjunto también confirmó inicialización y cierre offline de Discord.

La negociación DAVE y la llamada audible real siguen pendientes.
Consulta `RUNBOOK.md` y `VERIFICATION.md` para comandos y evidencia actual.
