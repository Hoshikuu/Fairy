const $ = id => document.getElementById(id);
const send = message => window.fairy.send(message);
let ready = false, busy = false, acceptAudio = false, audioContext, nextAudio = 0, playing = [], recorder, micStarting = false;
let shareStream, shareTimer;

function state(message) { $('status').textContent = message; }
function buttons() { $('send').disabled = !ready || busy || Boolean(recorder) || micStarting; $('mic').disabled = !ready || busy || micStarting; }
function bubble(text, role) {
  const item = document.createElement('div'); item.className = `bubble ${role}`; item.textContent = text;
  $('messages').appendChild(item); item.scrollIntoView({ block: 'end' });
}
function stopAudio() { for (const source of playing) { try { source.stop(); } catch {} } playing = []; nextAudio = 0; }
function audio() { if (!audioContext) audioContext = new AudioContext(); return audioContext; }
function play(encoded) {
  const bytes = Uint8Array.from(atob(encoded), char => char.charCodeAt(0));
  const pcm = new DataView(bytes.buffer); const ctx = audio();
  const buffer = ctx.createBuffer(1, bytes.length / 2, 24000); const channel = buffer.getChannelData(0);
  for (let i = 0; i < channel.length; i++) channel[i] = pcm.getInt16(i * 2, true) / 32768;
  const source = ctx.createBufferSource(); source.buffer = buffer; source.connect(ctx.destination);
  source.onended = () => { playing = playing.filter(item => item !== source); };
  nextAudio = Math.max(ctx.currentTime + 0.03, nextAudio); source.start(nextAudio); nextAudio += buffer.duration; playing.push(source);
}
function beginTurn(message) { stopAudio(); audio().resume(); acceptAudio = true; busy = true; buttons(); state('Thinking...'); send({ type: 'turn', ...message }); }
$('send').onclick = () => { const text = $('input').value.trim(); if (!text || busy || !ready) return; $('input').value = ''; bubble(text, 'user'); beginTurn({ text }); };
$('input').onkeydown = event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('send').click(); } };
$('stop').onclick = () => { acceptAudio = false; stopAudio(); send({ type: 'cancel' }); };
$('reset').onclick = () => { if (busy) return; send({ type: 'reset' }); $('messages').replaceChildren(); bubble('New conversation started.', 'fairy'); };
$('control').onclick = () => { const enabled = $('control').getAttribute('aria-pressed') !== 'true'; $('control').setAttribute('aria-pressed', String(enabled)); $('control').textContent = `Control: ${enabled ? 'on' : 'off'}`; send({ type: 'control', enabled }); };
$('vtube').onclick = () => { const enabled = $('vtube').getAttribute('aria-pressed') !== 'true'; $('vtube').setAttribute('aria-pressed', String(enabled)); $('vtube').textContent = `VTube: ${enabled ? 'on' : 'off'}`; send({ type: 'vtube', enabled }); };

function encodeAudio(samples, rate) {
  const length = Math.floor(samples.length * 16000 / rate); const bytes = new Uint8Array(length * 2); const view = new DataView(bytes.buffer);
  for (let i = 0; i < length; i++) { const pos = i * rate / 16000; const left = Math.floor(pos); const fraction = pos - left; const sample = samples[left] * (1 - fraction) + (samples[Math.min(left + 1, samples.length - 1)] || 0) * fraction; view.setInt16(i * 2, Math.max(-32768, Math.min(32767, sample * 32767)), true); }
  let binary = ''; for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192)); return btoa(binary);
}
async function startMic() {
  if (!ready || busy || recorder || micStarting) return;
  micStarting = true;
  buttons();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    const ctx = audio(); await ctx.resume(); const source = ctx.createMediaStreamSource(stream); const processor = ctx.createScriptProcessor(4096, 1, 1); const chunks = []; let count = 0;
    let spoke = false, quiet = 0;
    recorder = { stream, source, processor, chunks, rate: ctx.sampleRate }; source.connect(processor); processor.connect(ctx.destination);
    processor.onaudioprocess = event => {
      if (recorder?.processor !== processor) return;
      if (count >= ctx.sampleRate * 30) { finishMic(); return; }
      const chunk = new Float32Array(event.inputBuffer.getChannelData(0)); chunks.push(chunk); count += chunk.length;
      let energy = 0; for (let i = 0; i < chunk.length; i++) energy += chunk[i] * chunk[i];
      const rms = Math.sqrt(energy / chunk.length);
      if (rms > 0.025) { spoke = true; quiet = 0; }
      else if (spoke && rms < 0.012) quiet += chunk.length;
      else if (spoke) quiet = 0;
      if (spoke && quiet >= ctx.sampleRate * 1.8 && count >= ctx.sampleRate * 0.8) finishMic();
    };
    $('mic').textContent = 'Stop recording'; state('Listening...');
  } catch (error) { state(`Microphone: ${error.message}`); } finally { micStarting = false; buttons(); }
}
function finishMic() {
  if (!recorder) return; const current = recorder; recorder = null; current.processor.onaudioprocess = null; current.processor.disconnect(); current.source.disconnect(); current.stream.getTracks().forEach(track => track.stop());
  $('mic').textContent = 'Record'; const length = current.chunks.reduce((n, chunk) => n + chunk.length, 0); if (!length) { state('No audio recorded'); buttons(); return; }
  const samples = new Float32Array(length); let offset = 0; for (const chunk of current.chunks) { samples.set(chunk, offset); offset += chunk.length; }
  bubble('Voice message', 'user'); beginTurn({ audio: encodeAudio(samples, current.rate) });
}
$('mic').textContent = 'Record'; $('mic').onclick = () => recorder ? finishMic() : startMic();

function stopShare() { clearInterval(shareTimer); shareStream?.getTracks().forEach(track => track.stop()); shareStream = null; send({ type: 'clear_frame' }); $('screen').textContent = 'Share screen'; }
$('screen').onclick = async () => {
  if (shareStream) { stopShare(); return; }
  try {
    const sources = await window.fairy.sources(); $('sources').replaceChildren();
    for (const source of sources) { const button = document.createElement('button'); const img = document.createElement('img'); img.src = source.thumbnail; img.alt = ''; button.append(img, document.createTextNode(source.name));
      button.onclick = async () => { $('picker').close(); try {
        shareStream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { mandatory: { chromeMediaSource: 'desktop', chromeMediaSourceId: source.id, maxWidth: 1280, maxHeight: 720, maxFrameRate: 5 } } });
        const video = document.createElement('video'); video.srcObject = shareStream; await video.play(); const canvas = document.createElement('canvas');
        const frame = () => { if (!shareStream || !video.videoWidth) return; canvas.width = video.videoWidth; canvas.height = video.videoHeight; canvas.getContext('2d').drawImage(video, 0, 0); send({ type: 'frame', data: canvas.toDataURL('image/jpeg', 0.65).split(',')[1], width: canvas.width, height: canvas.height }); };
        shareStream.getVideoTracks()[0].onended = stopShare; $('screen').textContent = 'Stop sharing'; frame(); shareTimer = setInterval(frame, 3000);
      } catch (error) { state(`Screen: ${error.message}`); stopShare(); } }; $('sources').append(button); }
    $('picker').showModal();
  } catch (error) { state(`Screen: ${error.message}`); }
};
$('close-picker').onclick = () => $('picker').close();
window.fairy.onEvent(event => {
  if (event.type === 'status') state(event.message);
  else if (event.type === 'ready') { ready = true; $('dot').classList.add('ready'); state('Ready to chat'); buttons(); }
  else if (event.type === 'audio' && acceptAudio) play(event.data);
  else if (event.type === 'answer') { bubble(event.text, 'fairy'); busy = false; state('Ready to chat'); buttons(); }
  else if (event.type === 'cancelled') { busy = false; state('Response stopped'); buttons(); }
  else if (event.type === 'action') $('activity').textContent = `Fairy: ${event.message}`;
  else if (event.type === 'expression') $('activity').textContent = `Fairy: expression ${event.expression}`;
  else if (event.type === 'fatal') { ready = false; acceptAudio = false; stopAudio(); busy = false; $('dot').classList.remove('ready'); state(event.message); buttons(); }
  else if (event.type === 'error') { acceptAudio = false; stopAudio(); busy = false; state(event.message); buttons(); }
});
