"""Verification / Critic Agent - AURA's key differentiator.

Checks facts, sources, and calculations; flags hallucinations before results
reach the user.

How it works:
- Takes one or more AgentResult objects (from Document/Research agents) via context
- Splits each agent's output into individual sentences (claims)
- For each claim, finds which source(s) it cited (e.g. "[1]", "[2]")
- Runs NLI (roberta-large-mnli) to check whether the cited source actually
  supports (entailment), contradicts, or is unrelated to (neutral) the claim
- Returns ok=False only if a HIGH-CONFIDENCE contradiction is found. Low-
  confidence contradictions are reported but not treated as failures, since
  NLI models are less reliable on long, fact-dense premises and often
  produce low-confidence false positives.

Owner: Danish
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agents.base import AgentResult, BaseAgent
from agents.verifier.nli_checker import NLIChecker

# Below this confidence, a "contradiction" label is treated as uncertain
# rather than a real factual error (NLI models are less reliable on long,
# fact-dense premises, so low-confidence contradictions are often false positives)
CONTRADICTION_CONFIDENCE_THRESHOLD = 0.70


@dataclass
class ClaimCheck:
    claim: str
    cited_sources: list[int]
    label: str          # "entailment" | "neutral" | "contradiction" | "unverifiable"
    confidence: float
    source_used: str    # which source label was actually checked


class VerifierAgent(BaseAgent):
    name = "verifier"

    def __init__(self):
        self.nli = NLIChecker()

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """Verify claims in agent result(s) passed via context.

        Expects context = {"results_to_verify": [AgentResult, ...]}
        """
        results_to_verify = (context or {}).get("results_to_verify", [])

        if not results_to_verify:
            return AgentResult(
                agent=self.name,
                output="No agent results were provided to verify.",
                sources=[],
                ok=True,
            )

        all_checks: list[ClaimCheck] = []

        for agent_result in results_to_verify:
            checks = self._verify_agent_result(agent_result)
            all_checks.extend(checks)

        report, has_contradiction = self._build_report(all_checks)

        return AgentResult(
            agent=self.name,
            output=report,
            sources=[{"label": c.source_used, "text": c.claim} for c in all_checks],
            ok=not has_contradiction,
        )

    def _verify_agent_result(self, agent_result: AgentResult) -> list[ClaimCheck]:
        """Split one agent's output into claims and check each against its
        cited source(s)."""
        sentences = self._split_sentences(agent_result.output)
        checks: list[ClaimCheck] = []

        for sentence in sentences:
            cited_ids = self._extract_citations(sentence)
            clean_claim = self._strip_citations(sentence)

            if not clean_claim.strip():
                continue  # skip empty/citation-only fragments

            if not cited_ids:
                # No citation at all - can't verify against a source
                checks.append(ClaimCheck(
                    claim=clean_claim,
                    cited_sources=[],
                    label="unverifiable",
                    confidence=0.0,
                    source_used="(no citation)",
                ))
                continue

            # Check against the first cited source (simplest case; a claim
            # citing multiple sources is checked against the first for now)
            source_idx = cited_ids[0] - 1
            if source_idx < 0 or source_idx >= len(agent_result.sources):
                checks.append(ClaimCheck(
                    claim=clean_claim,
                    cited_sources=cited_ids,
                    label="unverifiable",
                    confidence=0.0,
                    source_used="(citation out of range)",
                ))
                continue

            source = agent_result.sources[source_idx]
            nli_result = self.nli.check(premise=source["text"], hypothesis=clean_claim)

            checks.append(ClaimCheck(
                claim=clean_claim,
                cited_sources=cited_ids,
                label=nli_result.label,
                confidence=nli_result.confidence,
                source_used=source["label"],
            ))

        return checks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Simple sentence splitter. Not perfect (doesn't handle abbreviations
        like 'e.g.'), but good enough for typical agent-generated prose."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s for s in sentences if s.strip()]

    @staticmethod
    def _extract_citations(sentence: str) -> list[int]:
        """Extract citation numbers like [1], [2] from a sentence."""
        return [int(n) for n in re.findall(r"\[(\d+)\]", sentence)]

    @staticmethod
    def _strip_citations(sentence: str) -> str:
        """Remove citation markers so the NLI model checks clean claim text."""
        return re.sub(r"\[\d+\]", "", sentence).strip()

    @staticmethod
    def _build_report(checks: list[ClaimCheck]) -> tuple[str, bool]:
        """Build a human-readable verification report."""
        total = len(checks)
        entailed = sum(1 for c in checks if c.label == "entailment")
        neutral = sum(1 for c in checks if c.label == "neutral")
        unverifiable = sum(1 for c in checks if c.label == "unverifiable")

        # Split contradictions by confidence: only high-confidence ones are
        # treated as real, actionable failures. Low-confidence ones are
        # likely NLI model uncertainty on long/complex premises, not genuine errors.
        all_contradictions = [c for c in checks if c.label == "contradiction"]
        strong_contradictions = [
            c for c in all_contradictions if c.confidence >= CONTRADICTION_CONFIDENCE_THRESHOLD
        ]
        weak_contradictions = [
            c for c in all_contradictions if c.confidence < CONTRADICTION_CONFIDENCE_THRESHOLD
        ]

        lines = [
            f"Verification Report: {total} claim(s) checked.",
            f"  Entailed (supported): {entailed}",
            f"  Neutral (unrelated to source): {neutral}",
            f"  Contradicted (high-confidence): {len(strong_contradictions)}",
            f"  Contradicted (low-confidence, review recommended): {len(weak_contradictions)}",
            f"  Unverifiable (no valid citation): {unverifiable}",
            "",
        ]

        if strong_contradictions:
            lines.append("HIGH-CONFIDENCE CONTRADICTIONS (likely real errors):")
            for c in strong_contradictions:
                lines.append(f'  - Claim: "{c.claim}"')
                lines.append(f"    Cited source: {c.source_used}")
                lines.append(f"    Confidence: {c.confidence:.2%}")
            lines.append("")

        if weak_contradictions:
            lines.append("LOW-CONFIDENCE CONTRADICTIONS (flagged for manual review, not treated as failures):")
            for c in weak_contradictions:
                lines.append(f'  - Claim: "{c.claim}"')
                lines.append(f"    Cited source: {c.source_used}")
                lines.append(f"    Confidence: {c.confidence:.2%}")
            lines.append("")

        has_real_contradiction = len(strong_contradictions) > 0
        lines.append("Overall: " + ("FAILED - high-confidence contradictions detected" if has_real_contradiction else "PASSED"))

        return "\n".join(lines), has_real_contradiction


if __name__ == "__main__":
    from agents.document.document_agent import DocumentAgent

    doc_agent = DocumentAgent()
    doc_result = doc_agent.run("Why did sales decline in the Karachi region?")

    print("=== Document Agent Output ===")
    print(doc_result.output)
    print()

    verifier = VerifierAgent()
    verify_result = verifier.run("verify", context={"results_to_verify": [doc_result]})

    print("=== Verification Result ===")
    print(verify_result.output)
    print(f"\nOk: {verify_result.ok}")