from array import array
import sys


FRAME_BYTES = 3840


def samples_from_pcm(pcm: bytes) -> array:
    if len(pcm) % 2:
        raise ValueError("PCM16 data must contain complete samples")
    samples = array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def samples_to_pcm(samples: array) -> bytes:
    if sys.byteorder != "little":
        samples = array("h", samples)
        samples.byteswap()
    return samples.tobytes()


def stereo_to_mono(pcm: bytes) -> bytes:
    samples = samples_from_pcm(pcm)
    if len(samples) % 2:
        raise ValueError("Stereo PCM must contain complete frames")
    mono = array("h", ((samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2)))
    return samples_to_pcm(mono)


def rms(pcm: bytes) -> float:
    samples = samples_from_pcm(pcm)
    if not samples:
        return 0.0
    return (sum(sample * sample for sample in samples) / len(samples)) ** 0.5


class Resampler:
    """Linear PCM16 mono resampling with state preserved across chunks."""

    def __init__(self, source_rate: int, target_rate: int):
        if source_rate <= 0 or target_rate <= 0:
            raise ValueError("Sample rates must be positive")
        self.source_rate = source_rate
        self.target_rate = target_rate
        self.samples = []
        self.position = 0

    def convert(self, pcm: bytes, *, final: bool = False) -> bytes:
        self.samples.extend(samples_from_pcm(pcm))
        if final and self.samples:
            self.samples.append(self.samples[-1])
        output = array("h")
        while self.position // self.target_rate + 1 < len(self.samples):
            index, fraction = divmod(self.position, self.target_rate)
            left = self.samples[index]
            right = self.samples[index + 1]
            output.append((left * (self.target_rate - fraction) + right * fraction) // self.target_rate)
            self.position += self.source_rate
        consumed = min(self.position // self.target_rate, max(0, len(self.samples) - 1))
        if consumed:
            del self.samples[:consumed]
            self.position -= consumed * self.target_rate
        return samples_to_pcm(output)


def mono_to_stereo(pcm: bytes) -> bytes:
    output = array("h")
    for sample in samples_from_pcm(pcm):
        output.extend((sample, sample))
    return samples_to_pcm(output)


def input_audio(pcm: bytes, target_rate: int) -> bytes:
    if target_rate == 16000:
        samples = samples_from_pcm(pcm)
        output = array("h")
        for index in range(0, len(samples) - 2, 3):
            output.append((samples[index] + samples[index + 1] + samples[index + 2]) // 3)
        return samples_to_pcm(output)
    return Resampler(48000, target_rate).convert(pcm, final=True)
