"""Record a short clip from the microphone and save as .wav.

Owner: (voice agent support)
"""
from __future__ import annotations

import sounddevice as sd
from scipy.io.wavfile import write

SAMPLE_RATE = 16000  # Whisper expects 16kHz, this matches well
DEFAULT_DEVICE = 2   # Microphone Array (Intel Smart Sound Technology), MME
                       # Change this if device 2 doesn't work - try 7 or 12 instead


def record_audio(duration: int = 5, output_path: str = "mic_recording.wav", device: int = DEFAULT_DEVICE) -> str:
    """Record `duration` seconds from the specified mic, save to output_path."""
    print(f"Recording for {duration} seconds... speak now.")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=device,
    )
    sd.wait()
    write(output_path, SAMPLE_RATE, audio)
    print(f"Saved recording to {output_path}")
    return output_path


if __name__ == "__main__":
    record_audio(duration=5, output_path="mic_recording.wav")