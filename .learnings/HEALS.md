## [HEAL-20261014-001] missing_kokoro_discord_output

**Logged**: 2026-10-14
**Status**: pending-verify
**Trigger**: missing-capability
**Area**: voice-pipeline
**Priority**: high

### Failure

El usuario indicó que el bot no hablaba en Discord después de añadir el servicio
Kokoro. La respuesta del LLM se publicaba exclusivamente por texto.

### Diagnosis

`VoiceTranscription._llm_loop` no llamaba a Kokoro y no existía ninguna ruta de
reproducción en Discord. Las pruebas anteriores verificaban WAV/servidor, no la
respuesta de voz del bot.

### Fix

Añadidos cliente HTTP, adaptador PCM y reproducción con callback, cola de voz,
comprobación de salud/voz/permisos en `/join` y cancelación al usar `/leave`.
Archivos: `kokoro_client.py`, `voice_transcription.py`, `bot.py`.

### Verification

30 pruebas automáticas pasan. Compilación y diff check correctos. El comprobador
`scripts/check_voice_pipeline.py` ejecutó los modelos reales de Whisper, llama y
Kokoro, y produjo 130 paquetes Opus de salida; el supervisor cerró con código 0.
La corrección está aplicada y verificada localmente. El estado se mantiene en
pending-verify porque no se ha conectado a Discord ni confirmado audio audible
en un canal real.

### Metadata

- Related Files: kokoro_client.py, voice_transcription.py, bot.py, docs/kokoro_pipeline_review.md
- Pattern-Key: voice.missing_tts_output_transport
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-10-14
