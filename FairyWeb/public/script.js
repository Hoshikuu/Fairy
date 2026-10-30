const mic = document.querySelector('#mic');
const statusText = document.querySelector('#status');
const detail = document.querySelector('#detail');
const caption = document.querySelector('#mic-caption');
const orb = document.querySelector('#orb');
const toggle = document.querySelector('#transcript-toggle');
const transcript = document.querySelector('#transcript');
const transcriptBody = transcript.querySelector('div');
let socket, stream, context, capture, analyser, frame, rate, outputRate, playbackEnd = 0;
let phase = 'idle', stopping = false, responseFinished = false, timer, textNode;
const playing = new Set();
function show(label, description, button, active = false) {
  statusText.textContent = label; detail.textContent = description; caption.textContent = button;
  mic.classList.toggle('active', active);
  mic.setAttribute('aria-pressed', String(active));
  mic.setAttribute('aria-label', active ? 'Enviar audio' : 'Iniciar conversación');
}
function send(message) { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message)); }
function addLine(label) {
  const p = document.createElement('p'); const strong = document.createElement('strong');
  strong.textContent = label + ': '; p.append(strong); transcriptBody.append(p); return p;
}
function reset(message = '') {
  phase = 'idle'; clearTimeout(timer); cancelAnimationFrame(frame);
  if (capture) capture.disconnect();
  stream?.getTracks().forEach(track => track.stop()); stream = null;
  playing.forEach(source => { try { source.stop(); } catch {} }); playing.clear();
  socket?.close(); socket = null;
  if (context) context.close().catch(() => {}); context = null; capture = null;
  orb.style.transform = ''; playbackEnd = 0;
  show(message || 'Lista para conversar', message ? 'Comprueba que llama-server esté funcionando y vuelve a intentarlo.' : 'Pulsa para hablar; vuelve a pulsar para enviar.', 'INICIAR CONVERSACIÓN');
}
function animate() {
  if (!analyser || !context) return;
  const data = new Uint8Array(analyser.frequencyBinCount); analyser.getByteFrequencyData(data);
  const level = data.reduce((sum, value) => sum + value, 0) / data.length;
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) orb.style.transform = `scale(${1 + Math.min(level / 350, 0.2)})`;
  frame = requestAnimationFrame(animate);
}
function finishPlayback() {
  if (!responseFinished || playing.size || phase !== 'responding') return;
  phase = 'ready'; show('Respuesta terminada', 'Pulsa el micrófono para continuar la conversación.', 'HABLAR DE NUEVO');
}
function playAudio(base64) {
  const bytes = Uint8Array.from(atob(base64), char => char.charCodeAt(0));
  const view = new DataView(bytes.buffer); const samples = Math.floor(bytes.length / 2);
  const buffer = context.createBuffer(1, samples, outputRate);
  const channel = buffer.getChannelData(0);
  for (let i = 0; i < samples; i++) channel[i] = view.getInt16(i * 2, true) / 32768;
  const source = context.createBufferSource(); source.buffer = buffer; source.connect(context.destination);
  source.onended = () => { playing.delete(source); finishPlayback(); };
  playing.add(source); playbackEnd = Math.max(playbackEnd, context.currentTime + .04); source.start(playbackEnd); playbackEnd += buffer.duration;
  show('Fairy está hablando', 'Escuchando respuesta en streaming.', 'RESPONDIENDO');
}
function handleEvent(event) {
  const data = JSON.parse(event.data);
  if (data.type === 'session.created') {
    rate = data.session.audio.input.format.rate; outputRate = data.session.audio.output.format.rate;
    send({ type: 'session.update', session: { type: 'realtime', instructions: 'Respond in interleaved text and audio.', output_modalities: ['text', 'audio'], max_output_tokens: 512 } });
  } else if (data.type === 'session.updated' && phase === 'connecting') {
    phase = 'recording'; capture.port.postMessage({ type: 'start', rate });
    show('Escuchando...', 'Habla y pulsa el micrófono para enviar.', 'ENVIAR AUDIO', true);
  } else if (data.type === 'response.output_text.delta' || data.type === 'response.output_audio_transcript.delta') {
    if (!textNode) textNode = addLine('Fairy'); textNode.append(document.createTextNode(data.delta || ''));
  } else if (data.type === 'response.output_audio.delta') playAudio(data.delta);
  else if (data.type === 'response.done') { responseFinished = true; finishPlayback(); }
  else if (data.type === 'error') { console.error(data.error); reset(data.error?.message || 'Error del servidor'); }
}
async function start() {
  phase = 'connecting'; show('Conectando...', 'Preparando micrófono y modelo local.', 'CONECTANDO');
  try {
    context = new AudioContext(); await context.resume();
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    await context.audioWorklet.addModule('audio-worklet.js');
    const source = context.createMediaStreamSource(stream);
    analyser = context.createAnalyser(); source.connect(analyser); analyser.fftSize = 256; animate();
    capture = new AudioWorkletNode(context, 'microphone-capture'); source.connect(capture);
    const mute = context.createGain(); mute.gain.value = 0; capture.connect(mute); mute.connect(context.destination);
    capture.port.onmessage = ({ data }) => {
      if (data.type === 'stopped') { if (stopping) { stopping = false; send({ type: 'input_audio_buffer.commit' }); send({ type: 'response.create' }); } return; }
      const bytes = new Uint8Array(data); let binary = '';
      for (const byte of bytes) binary += String.fromCharCode(byte);
      send({ type: 'input_audio_buffer.append', audio: btoa(binary) });
    };
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/v1/realtime`);
    socket.onmessage = handleEvent;
    socket.onerror = () => reset('No se pudo conectar con el modelo');
    socket.onclose = () => { if (phase !== 'idle') reset('Conexión cerrada'); };
  } catch (error) { console.error(error); reset('No se pudo acceder al micrófono'); }
}
mic.addEventListener('click', () => {
  if (phase === 'idle') { start(); return; }
  if (phase === 'ready') { textNode = null; responseFinished = false; phase = 'recording'; capture.port.postMessage({ type: 'start', rate }); show('Escuchando...', 'Habla y pulsa el micrófono para enviar.', 'ENVIAR AUDIO', true); return; }
  if (phase !== 'recording') return;
  phase = 'responding'; stopping = true; capture.port.postMessage({ type: 'stop' });
  // A turn can end exactly on a chunk boundary; flush acknowledgment always arrives.
  show('Procesando...', 'Fairy está preparando una respuesta.', 'PROCESANDO');
});
function setTranscript(open) { transcript.hidden = !open; toggle.setAttribute('aria-expanded', String(open)); }
toggle.addEventListener('click', () => setTranscript(transcript.hidden));
document.querySelector('#close-transcript').addEventListener('click', () => { setTranscript(false); toggle.focus(); });
const about = document.querySelector('#about');
document.querySelector('.help').addEventListener('click', () => about.showModal());
document.querySelector('#close-about').addEventListener('click', () => about.close());
window.addEventListener('pagehide', () => reset());
show('Lista para conversar', 'Pulsa para hablar; vuelve a pulsar para enviar.', 'INICIAR CONVERSACIÓN');


