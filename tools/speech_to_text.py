"""Speech-to-text tool using Groq-hosted Whisper Large v3.

Owner: Ahmad (tools) / voice agent support
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """Transcribe an audio file to text using Whisper Large v3."""
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(Path(audio_path).name, f.read()),
            model="whisper-large-v3",
            language=language,
            response_format="json",
            temperature=0.0,
        )
    return transcription.text


if __name__ == "__main__":
    text = transcribe_audio("sample_audio.wav")
    print("Transcribed text:", text)