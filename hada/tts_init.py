#   ----------------------------------------------------
#          Hoshikuu - https://github.com/Hoshikuu
#   ----------------------------------------------------
#   HadaAI/hada/tts_init.py - V0.1.0

import os
import sys
import threading
import queue
import traceback
import numpy as np
import librosa
import sounddevice as sd
import torch

from RealtimeTTS import TextToAudioStream
from RealtimeTTS.engines.kokoro_engine import KokoroEngine

from hada.utils.infer.modules import VC
from hada.utils.infer.utils import load_hubert
from hada.utils.configs.config import Config
from hada.utils.rmvpe import RMVPE

import fairseq
torch.serialization.add_safe_globals([fairseq.data.dictionary.Dictionary])

KOKORO_SR    = 24000
INTERNAL_SR  = 16000
PLAYBACK_SR  = 48000
# FIX 1: buffers más grandes para dar contexto a RVC
BUFFER_S     = 1.0   # era 0.4 → mínimo 1s para RVC
OVERLAP_S    = 0.1   # era 0.05 → 100ms de solapamiento

# ──────────────────────────────────────────────────────────────────────
_orig_argv = sys.argv.copy()
sys.argv = [sys.argv[0]]
_config = Config()
_config.device = "cuda" if torch.cuda.is_available() else "cpu"
_config.is_half = _config.device == "cuda"
sys.argv = _orig_argv

_vc = VC(_config)
_vc.get_vc("hada/voices/hada.pth", "hada/voices/hada.index")
_vc.hubert_model = load_hubert(_config)

_rmvpe = RMVPE(
    "hada/models/rmvpe/rmvpe.pt",
    is_half=_config.is_half,
    device=_config.device
)
_vc.pipeline.model_rmvpe = _rmvpe
print(f"[HadaVoice] Modelos listos en {_config.device.upper()}")

# ──────────────────────────────────────────────────────────────────────
class HadaVoicePipeline:
    def __init__(self):
        self.engine = KokoroEngine(voice="ef_dora")
        self.tts = TextToAudioStream(self.engine)

        self._raw_buf  = bytearray()
        self._threshold = int(KOKORO_SR * BUFFER_S) * 2  # bytes int16
        self._rvc_q    = queue.Queue()
        # FIX 2: cola de audio ya procesado como numpy arrays concatenados
        self._play_q   = queue.Queue()

        self._text_buf = ""

        threading.Thread(target=self._rvc_worker,      daemon=True).start()
        threading.Thread(target=self._playback_worker, daemon=True).start()

    # ── Callbacks ───────────────────────────────────────────────────
    def _on_chunk(self, chunk: bytes):
        self._raw_buf.extend(chunk)
        if len(self._raw_buf) >= self._threshold:
            self._rvc_q.put(bytes(self._raw_buf))
            self._raw_buf.clear()

    def _on_sentence(self, sentence: str):
        if self._raw_buf:
            self._rvc_q.put(bytes(self._raw_buf))
            self._raw_buf.clear()
        self._rvc_q.put(b"__EOF__")

    # ── RVC worker ──────────────────────────────────────────────────
    def _rvc_worker(self):
        buf      = np.array([], dtype=np.float32)
        buf_size = int(INTERNAL_SR * BUFFER_S)
        overlap  = int(INTERNAL_SR * OVERLAP_S)

        while True:
            item = self._rvc_q.get()

            if item == b"__EOF__":
                if len(buf) > overlap:
                    self._infer(buf)
                buf = np.array([], dtype=np.float32)
                self._play_q.put(None)  # señal de fin de frase
                continue

            chunk = np.frombuffer(item, dtype=np.int16).astype(np.float32) / 32768.0
            if KOKORO_SR != INTERNAL_SR:
                chunk = librosa.resample(chunk, orig_sr=KOKORO_SR, target_sr=INTERNAL_SR)

            buf = np.concatenate((buf, chunk))
            while len(buf) >= buf_size:
                self._infer(buf[:buf_size])
                buf = buf[buf_size - overlap:]

    def _infer(self, audio: np.ndarray):
        try:
            _, (out_sr, out_data) = _vc.vc_single(
                0, (INTERNAL_SR, audio), 2, None, "rmvpe",
                "hada.index", None, 0.75, 3, 0, 0.25, 0.33
            )
            # FIX 3: normalizar y resamplear aquí, antes de encolar
            processed = out_data.astype(np.float32) / (np.max(np.abs(out_data)) + 1e-9)
            if out_sr != PLAYBACK_SR:
                processed = librosa.resample(processed, orig_sr=out_sr, target_sr=PLAYBACK_SR)
            self._play_q.put(processed)
        except Exception:
            traceback.print_exc()

    # ── Playback worker — FIX 4: stream persistente ─────────────────
    def _playback_worker(self):
        """Maneja el overlap sin duplicar audio y con buffer seguro."""
        # El crossfade DEBE ser exactamente igual al overlap de RVC
        xfade_samples = int(PLAYBACK_SR * OVERLAP_S)
        prev_tail = None

        with sd.OutputStream(
            samplerate=PLAYBACK_SR,
            channels=1,
            dtype="float32",
            blocksize=8192,  # Mayor blocksize absorbe retrasos de RVC
            latency=0.1      # Buffer de 100ms a nivel de OS
        ) as stream:
            while True:
                item = self._play_q.get()

                if item is None:
                    # Fin de frase: reproducir la cola retenida y limpiar
                    if prev_tail is not None:
                        stream.write(prev_tail.astype(np.float32).reshape(-1, 1))
                        prev_tail = None
                    stream.write(np.zeros((int(PLAYBACK_SR * 0.05), 1), dtype=np.float32))
                    continue

                audio = item
                
                # Salvaguarda: si el chunk final de Kokoro es extremadamente pequeño
                if len(audio) <= xfade_samples:
                    if prev_tail is not None:
                        stream.write(prev_tail.astype(np.float32).reshape(-1, 1))
                        prev_tail = None
                    stream.write(audio.astype(np.float32).reshape(-1, 1))
                    continue

                if prev_tail is None:
                    # PRIMER CHUNK: Retenemos el final, reproducimos el resto
                    prev_tail = audio[-xfade_samples:].copy()
                    out = audio[:-xfade_samples]
                    stream.write(out.astype(np.float32).reshape(-1, 1))
                else:
                    # CHUNKS INTERMEDIOS: Fusionamos la cola retenida con el inicio actual
                    fade_in  = np.linspace(0, 1, xfade_samples, dtype=np.float32)
                    fade_out = np.linspace(1, 0, xfade_samples, dtype=np.float32)
                    
                    crossfaded = (audio[:xfade_samples] * fade_in) + (prev_tail * fade_out)
                    
                    # Retenemos la nueva cola para el siguiente ciclo
                    prev_tail = audio[-xfade_samples:].copy()
                    
                    # Ensamblamos: crossfade + centro del audio (sin la cola)
                    out = np.concatenate((crossfaded, audio[xfade_samples:-xfade_samples]))
                    stream.write(out.astype(np.float32).reshape(-1, 1))

    # ── API pública ─────────────────────────────────────────────────
    def speak(self, text: str, flush_force):
        self._text_buf += text

        flush = False
        if any(x in self._text_buf for x in ".!?\n"):
            flush = True
        elif len(self._text_buf) >= 80:
            flush = True

        if flush or flush_force:
            self.tts.feed(self._text_buf)
            self._text_buf = ""

            if not self.tts.is_playing():
                self.tts.play_async(
                    muted=True,
                    on_audio_chunk=self._on_chunk,
                    on_sentence_synthesized=self._on_sentence,
                    fast_sentence_fragment=True,
                    buffer_threshold_seconds=0.1
                )

# ──────────────────────────────────────────────────────────────────────
pipeline = HadaVoicePipeline()

def speak(text: str, flush: bool = False):
    pipeline.speak(text, flush)