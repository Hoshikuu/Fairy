class MicrophoneCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.enabled = false;
    this.ratio = 1;
    this.position = 0;
    this.samples = [];
    this.port.onmessage = ({ data }) => {
      if (data.type === 'start') { this.enabled = true; this.ratio = sampleRate / data.rate; this.position = 0; this.samples = []; }
      if (data.type === 'stop') { this.flush(); this.enabled = false; this.port.postMessage({ type: 'stopped' }); }
    };
  }
  flush() { if (this.samples.length) { this.port.postMessage(new Int16Array(this.samples).buffer); this.samples = []; } }
  process(inputs) {
    const input = inputs[0]?.[0];
    if (!this.enabled || !input) return true;
    while (this.position < input.length) {
      const sample = Math.max(-1, Math.min(1, input[Math.floor(this.position)]));
      this.samples.push(sample < 0 ? sample * 32768 : sample * 32767);
      this.position += this.ratio;
      if (this.samples.length >= 2048) this.flush();
    }
    this.position -= input.length;
    return true;
  }
}
registerProcessor('microphone-capture', MicrophoneCapture);

