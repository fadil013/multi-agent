"""NLI-based claim verification using roberta-large-mnli.

Checks whether a claim is entailed by, contradicted by, or unrelated to
its cited source text.

Owner: Manan (verification support)
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = "roberta-large-mnli"

# Model's label order: contradiction=0, neutral=1, entailment=2
LABELS = ["contradiction", "neutral", "entailment"]


@dataclass
class NLIResult:
    label: str          # "entailment" | "neutral" | "contradiction"
    confidence: float    # 0.0 - 1.0


class NLIChecker:
    def __init__(self):
        print(f"Loading {MODEL_NAME} (this may take a moment the first time)...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        self.model.eval()  # inference mode, no gradient tracking needed

    def check(self, premise: str, hypothesis: str) -> NLIResult:
        """premise = source text (the retrieved chunk/search result)
        hypothesis = the claim being verified (a sentence from the agent's answer)
        """
        inputs = self.tokenizer(
            premise, hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        with torch.no_grad():
            logits = self.model(**inputs).logits

        probs = torch.softmax(logits, dim=1)[0]
        predicted_idx = int(torch.argmax(probs))

        return NLIResult(
            label=LABELS[predicted_idx],
            confidence=float(probs[predicted_idx]),
        )


if __name__ == "__main__":
    checker = NLIChecker()

    # Test case 1: should be entailment
    result = checker.check(
        premise="Q2 2026 revenue in Karachi was $5.1M, a 25% year-over-year decline.",
        hypothesis="Karachi sales declined 25% in Q2 2026.",
    )
    print(f"Test 1 (should be entailment): {result.label} ({result.confidence:.2%})")

    # Test case 2: should be contradiction
    result = checker.check(
        premise="Q2 2026 revenue in Karachi was $5.1M, a 25% year-over-year decline.",
        hypothesis="Karachi sales declined 35% in Q2 2026.",
    )
    print(f"Test 2 (should be contradiction): {result.label} ({result.confidence:.2%})")

    # Test case 3: should be neutral
    result = checker.check(
        premise="Q2 2026 revenue in Karachi was $5.1M, a 25% year-over-year decline.",
        hypothesis="The company plans to open a new store in Lahore next year.",
    )
    print(f"Test 3 (should be neutral): {result.label} ({result.confidence:.2%})")