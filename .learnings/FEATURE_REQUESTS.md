# Funciones pendientes

## [FEAT-20261031-001] Ver transmisiones Go Live

**Status**: blocked by current Discord bot integration
**Summary**: Fairy debe utilizar las transmisiones de Discord como contexto visual para responder y comentar.
**Details**: El receptor actual solo procesa audio. La librería de vídeo investigada `discord-native-voice` declara compatibilidad con `discord.py-self`, no con `discord.py`. No se ha demostrado una ruta Go Live compatible con la cuenta de bot actual.
**Revalidation**: Revisar si Discord y una librería compatible con cuentas de bot exponen recepción de vídeo; alternativamente estudiar una fuente explícita de imágenes fuera de Discord.
**Evidence**: https://github.com/dolfies/discord-native-voice
