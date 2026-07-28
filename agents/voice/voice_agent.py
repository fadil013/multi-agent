"""Voice Agent - speech interface wrapper around ManagerAgent.

Converts spoken input to text (Whisper), runs it through the existing
multi-agent pipeline, then converts the text answer back to speech (Orpheus).

Owner: (assign)
"""
from __future__ import annotations

from agents.base import AgentResult, BaseAgent
from agents.manager.agent_manager import ManagerAgent
from tools.speech_to_text import transcribe_audio
from tools.text_to_speech import synthesize_speech


class VoiceAgent(BaseAgent):
    name = "voice"

    def __init__(self, manager: ManagerAgent):
        self.manager = manager

    def run_from_audio(self, audio_path: str, output_audio_path: str = "response.wav") -> dict:
        """Full voice pipeline: audio in -> ManagerAgent -> audio out."""
        goal_text = transcribe_audio(audio_path)
        print(f"Transcribed goal: {goal_text}")

        result: AgentResult = self.manager.run(goal_text)

        audio_out = synthesize_speech(result.output, output_path=output_audio_path)

        return {
            "transcribed_goal": goal_text,
            "text_answer": result.output,
            "audio_response_path": audio_out,
            "ok": result.ok,
        }

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """BaseAgent conformance - treats `task` as a text goal, not audio."""
        result = self.manager.run(task)
        audio_out = synthesize_speech(result.output)
        return AgentResult(
            agent=self.name,
            output=result.output,
            sources=result.sources,
            ok=result.ok,
        )


if __name__ == "__main__":
    from agents.document.document_agent import DocumentAgent
    from agents.researcher.research_agent import ResearchAgent
    from tools.record_audio import record_audio

    manager = ManagerAgent(agents={
        "document": DocumentAgent(),
        "research": ResearchAgent(),
    })

    voice_agent = VoiceAgent(manager)

    audio_path = record_audio(duration=6, output_path="mic_recording.wav")
    result = voice_agent.run_from_audio(audio_path)

    print("\nText answer:", result["text_answer"])
    print("Audio saved to:", result["audio_response_path"])