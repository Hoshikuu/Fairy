# Operación de Fairy

## Inicio de escritorio actual

En la raíz, ejecuta `python setup.py --yes`. Después, en `desktop/`, ejecuta `npm install`; vuelve a la raíz y ejecuta `./.venv/Scripts/python.exe main.py --check` y `./.venv/Scripts/python.exe main.py`. Espera a que la aplicación indique que los modelos están listos. Cierra la ventana para detenerlos. Consulta el README para grabación, pantalla y control. En este inicio no se usa token de Discord ni se arranca la web antigua.

Las secciones siguientes describen la versión anterior basada en Discord; los parámetros de los modelos siguen siendo útiles.

1. Instala Python 3.15, Git y un driver NVIDIA compatible con CUDA 13.4.
2. Ejecuta `python setup.py --yes` desde la raíz. Setup prepara la `.venv`, llama.cpp, MiniCPM Q4_K_M, LFM3 Q4_K_M, su proyector y DSpark Q4_K_M en `models/`. Para preparar solo modelos usa `python setup.py --yes --only models`.
3. Define `TOKEN` en `.env` y habilita Message Content Intent en el portal de Discord.
4. Ejecuta `./.venv/Scripts/python.exe setup.py --check --verify-models` y `./.venv/Scripts/python.exe main.py --check`. No inician sesión en Discord ni prueban las modalidades.
5. Ejecuta `./.venv/Scripts/python.exe main.py`, espera a los dos modelos y al login, entra en un canal de voz normal y usa `/join`. Usa `/leave` para desconectar y `q` + Enter para cerrar Fairy.

## Puertos y recursos

LFM3 usa `--port` (8080 por defecto); `FAIRY_OMNI_URL`, si se define, debe coincidir. MiniCPM usa el puerto de `FAIRY_BRAIN_URL` (8082 por defecto), y la web usa `--web-port` (8081). Se requieren tres puertos locales distintos. Si alguno está ocupado, elige otro; Fairy no termina procesos ajenos.

`FAIRY_BRAIN_MODEL_PATH`, `FAIRY_BRAIN_GPU_LAYERS`, `FAIRY_CONTEXT_SIZE` y `FAIRY_REASONING_MODE` configuran MiniCPM. `FAIRY_OMNI_MODEL_PATH`, `FAIRY_OMNI_PROJECTOR_PATH`, `FAIRY_OMNI_CONTEXT` y `FAIRY_OMNI_GPU_LAYERS` configuran LFM3. Si falta memoria, reduce contexto o capas GPU y mide la latencia. La prueba simultánea previa registró 6023 de 8188 MiB ocupados, incluidos otros procesos; no garantiza margen para cargas prolongadas.

## Discord y pantalla

El bot necesita permisos para conectar, hablar y enviar mensajes. Los canales Stage no están soportados. `/ask` y las menciones abren conversación por texto; `/reset` borra ese contexto. La voz se procesa por usuario mientras Fairy está conectada y el contexto se pierde al desconectar. No se generan comentarios espontáneos por inactividad.

Para mostrar la pantalla, abre `http://127.0.0.1:8081`, introduce tu ID de Discord y pulsa **Compartir pantalla**. Elige una ventana o pantalla y pregunta a Fairy por ella mediante texto o voz en Discord. MiniCPM decide si llama a `view_screen`; LFM3 analiza el fotograma reciente del ID correspondiente y MiniCPM genera la respuesta. La web solo contiene información y pantalla compartida. Detén la captura con el botón o cerrando la página. Consulta `docs/WEB_LOCAL.md`.

Comprueba recepción, transcripción, interrupción, salida audible y pantalla con personas y dispositivos reales. La detección por energía puede fallar con ruido. Las pruebas previas con ambos modelos reales no sustituyen una llamada Discord; esta sigue pendiente. No publiques los endpoints locales.
