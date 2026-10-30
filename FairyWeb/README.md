# FairyWeb

Demo local de voz con LFM3-Omni-2B y llama.cpp b11960. El navegador captura audio y lo envía por WebSocket a llama-server. El modelo genera texto y voz por fragmentos; el navegador reproduce el audio mientras llega. No se envía audio a servicios externos.

## Inicio

Desde la raíz ejecuta `python FairyWeb/app.py`, o abre `FairyWeb/start.bat` en Windows. El lanzador usa solo la biblioteca estándar de Python. Espera a que aparezca `model loaded` y abre http://127.0.0.1:8090. Concede permiso al micrófono, pulsa el botón para hablar y vuelve a pulsarlo para enviar. Cuando termine la respuesta, pulsa de nuevo para continuar. Usa Ctrl+C en la ventana del servidor para detenerlo.

El modelo y el proyector GGUF deben permanecer en esta carpeta. El servidor usa la RTX mediante CUDA, puerto 8090 y escucha exclusivamente en localhost. Si el puerto está ocupado, detén el proceso correspondiente o ejecuta `python FairyWeb/app.py --port 8091` y utiliza el nuevo puerto en la URL. `--check` comprueba los archivos sin arrancar el modelo. Los binarios de llama.cpp y las bibliotecas CUDA se encuentran en `llama/`, separados de la instalación principal de Fairy.

La conversación de voz funciona mejor en inglés. El sistema de turnos es manual: no incluye detección de silencio ni interrupción de respuestas. La transcripción muestra las respuestas del modelo, no lo que dice el usuario. El modelo mantiene el contexto mientras la página siga conectada; al recargar se pierde. No incluye autenticación y está diseñado solo para uso local.

## Comprobaciones

Se ha probado `/health`, la página y una sesión WebSocket con voz sintetizada como entrada. El modelo respondió con texto y audio PCM. Falta verificar una conversación audible con micrófono físico y altavoces en el navegador del usuario.

Documentación: [modelo GGUF](https://huggingface.co/LiquidAI/LFM3-Omni-2B-GGUF) y [API realtime de llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#realtime-conversation).

