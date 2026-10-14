"""Explain decision distributions without changing action confidence gates."""

import math
import statistics


def distribution_metrics(probabilities: dict[str, float]) -> dict:
    values = list(probabilities.values())
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        raise ValueError("invalid decision probabilities")
    n = len(values)
    ordered = sorted(values, reverse=True)
    total = sum(values)
    normalized = [value / total for value in values] if total > 0 else []
    entropy = (
        -sum(p * math.log(p) for p in normalized if p) / math.log(n)
        if n > 1 and normalized
        else None
    )
    return {
        "probabilities": dict(probabilities),
        "option_count": n,
        "classification": (
            "ABSENT"
            if not n
            else "SINGLETON"
            if n == 1
            else "UNIFORM"
            if max(values) - min(values) <= 1e-4
            else "NONUNIFORM"
        ),
        "normalized_entropy": entropy,
        "probability_stdev": statistics.pstdev(values) if n > 1 else None,
        "top_two_margin": ordered[0] - ordered[1] if n > 1 else None,
        "raw_logit_variance": None,
        "repeat_invariance": "NOT_MEASURED",
        "singleton_is_safety_evidence": False,
    }
