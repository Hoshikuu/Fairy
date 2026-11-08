const $ = selector => document.querySelector(selector);
let language = 'en';
let screen = null;
let socket = null;
let timer = null;
let sending = false;
const preview = $('#preview');
const canvas = document.createElement('canvas');
const context = canvas.getContext('2d');

function translate(next) {
  language = next;
  document.documentElement.lang = next;
  document.querySelectorAll('[data-en][data-es]').forEach(element => {
    element.textContent = element.dataset[next];
  });
  const button = $('#language');
  button.textContent = next === 'en' ? 'Español' : 'English';
  button.setAttribute('aria-label', next === 'en' ? 'Cambiar idioma a español' : 'Switch language to English');
  try { localStorage.setItem('fairy-language', next); } catch {}
}
$('#language').addEventListener('click', () => translate(language === 'en' ? 'es' : 'en'));
try { if (localStorage.getItem('fairy-language') === 'es') translate('es'); } catch {}

function screenMessage(en, es) { $('#screen-status').textContent = language === 'en' ? en : es; }
function stopShare() {
  clearInterval(timer); timer = null;
  const previousSocket = socket; socket = null;
  if (previousSocket) previousSocket.close();
  const previousScreen = screen; screen = null;
  previousScreen?.getTracks().forEach(track => track.stop());
  preview.srcObject = null; preview.hidden = true; $('#preview-empty').hidden = false;
  $('#share').disabled = false; $('#stop-share').disabled = true; $('#discord-id').disabled = false;
}
async function sendFrame() {
  if (sending || !screen || socket?.readyState !== WebSocket.OPEN || socket.bufferedAmount > 0 || !preview.videoWidth) return;
  const connection = socket;
  sending = true;
  try {
    const scale = Math.min(1, 1280 / Math.max(preview.videoWidth, preview.videoHeight));
    canvas.width = Math.max(1, Math.round(preview.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(preview.videoHeight * scale));
    context.drawImage(preview, 0, 0, canvas.width, canvas.height);
    const image = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .75));
    if (image && image.size <= 1024 * 1024 && socket === connection && connection.readyState === WebSocket.OPEN) connection.send(image);
  } catch {
    stopShare();
    screenMessage('Unable to capture the selected screen. Try sharing again.', 'No se pudo capturar la pantalla seleccionada. Vuelve a compartirla.');
  } finally { sending = false; }
}
$('#share').addEventListener('click', async () => {
  const id = $('#discord-id').value.trim();
  if (!/^[0-9]{15,20}$/.test(id)) {
    screenMessage('Enter a valid Discord user ID (15–20 digits).', 'Introduce un ID de usuario de Discord válido (15–20 dígitos).');
    return;
  }
  $('#share').disabled = true;
  try {
    screen = await navigator.mediaDevices.getDisplayMedia({video: {frameRate: 1}, audio: false});
    const sharedScreen = screen;
    preview.srcObject = screen; preview.hidden = false; $('#preview-empty').hidden = true;
    screen.getVideoTracks()[0].addEventListener('ended', () => {
      if (screen !== sharedScreen) return;
      stopShare(); screenMessage('Screen sharing stopped.', 'Pantalla compartida detenida.');
    });
    const connection = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/screen?user_id=${encodeURIComponent(id)}`);
    socket = connection;
    connection.onopen = () => {
      if (socket !== connection) return;
      $('#stop-share').disabled = false; $('#discord-id').disabled = true;
      screenMessage('Sharing locally. Ask Fairy about your screen in Discord.', 'Compartiendo en local. Pregunta a Fairy por tu pantalla en Discord.');
      sendFrame(); timer = setInterval(sendFrame, 3000);
    };
    connection.onclose = () => {
      if (socket !== connection) return;
      stopShare(); screenMessage('Screen connection closed. Check the ID and try again.', 'Conexión de pantalla cerrada. Comprueba el ID e inténtalo de nuevo.');
    };
  } catch {
    stopShare(); screenMessage('Screen sharing was cancelled or unavailable.', 'Se canceló la captura o no está disponible.');
  }
});
$('#stop-share').addEventListener('click', () => { stopShare(); screenMessage('Screen sharing stopped.', 'Pantalla compartida detenida.'); });

window.addEventListener('pagehide', stopShare);
