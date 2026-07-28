"""Text-to-speech tool using Groq-hosted Orpheus (English).

Owner: Ahmad (tools) / voice agent support
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def synthesize_speech(text: str, output_path: str = "output.wav", voice: str = "troy") -> str:
    """Convert text to spoken audio, saved as a .wav file. Returns the path."""
    response = client.audio.speech.create(
        model="canopylabs/orpheus-v1-english",
        voice=voice,
        input=text,
        response_format="wav",
    )
    response.write_to_file(output_path)
    return output_path


if __name__ == "__main__":
    path = synthesize_speech("Hello, this is a test of the Orpheus text to speech system.")
    print("Audio saved to:", path)