# Fairy web local

La siguiente página corresponde a la versión anterior de Discord. La aplicación Electron actual no inicia esta web y usa su propia captura de pantalla. No se debe publicar ninguno de los servicios locales sin diseñar y verificar autenticación, HTTPS y controles de acceso.

La web se inicia con `main.py` y escucha solo en `127.0.0.1:8081`. Contiene información del proyecto y el apartado para compartir una pantalla o ventana con Fairy. La conversación y la voz se realizan en Discord.

También puede iniciarse por separado con `./.venv/Scripts/python.exe -m fairy.web --port 8081`. Para que Fairy analice la pantalla durante una conversación, el bot y los modelos deben estar funcionando en el mismo proceso principal; la web independiente solo ofrece la página y recibe fotogramas.

## Compartir pantalla

1. Abre `http://127.0.0.1:8081`, introduce tu ID de usuario de Discord y pulsa **Compartir pantalla**.
2. Selecciona una pantalla o ventana en el selector del navegador.
3. Entra en un canal de voz, usa `/join` y pregunta a Fairy por el contenido compartido.
4. Pulsa **Dejar de compartir** o cierra la página para detener la captura y eliminar sus fotogramas.

MiniCPM decide si solicita la herramienta de pantalla. LFM3 analiza el último fotograma para la pregunta y devuelve observaciones; MiniCPM produce la respuesta final. La decisión y el análisis pueden fallar. Esto no recibe transmisiones Discord Go Live.

El navegador envía un JPEG cada tres segundos, con el lado mayor limitado a 1280 píxeles y un máximo de 1 MiB. No captura micrófono ni audio del sistema. Se admiten hasta ocho usuarios; los fotogramas permanecen solo en memoria, caducan tras ocho segundos y se eliminan al cerrar la conexión. La página aplica contrapresión si el envío anterior sigue pendiente.

El ID introducido no está autenticado: otra persona con acceso local podría hacerse pasar por ese usuario. Mantén el servicio en localhost y comparte solo contenido que aceptes enviar al modelo. La captura requiere permiso del navegador.

El servicio no está preparado ni probado para exposición pública. La publicación necesitará HTTPS, autenticación apropiada y control de acceso. No se ha comprobado captura física de pantalla en este equipo.
