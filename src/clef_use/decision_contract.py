"""Model-independent typed decision answers; invalid outputs never reach input execution."""

from __future__ import annotations

import math

PROBABILITY_TOLERANCE = 1e-4


def _number(value, lower, upper, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"invalid decision answer {label}: expected finite [{lower}, {upper}]")
    return value


def validate_answers(questions: dict, reply: dict, *, answer_decimals: int | None = None) -> dict:
    # CLEF serializes native probabilities/scores to four decimals; d1 does not.
    # Bound the resulting rounding error without clipping or renormalizing data.
    rounding_error = 0 if answer_decimals is None else 0.5 * 10 ** (-answer_decimals)
    answers = reply.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("decision answers must match all submitted question names")
    if "usage" in reply and reply["usage"].get("output_tokens") != 0:
        raise ValueError("System One decisions must generate zero output tokens")
    for name, question in questions.items():
        answer = answers[name]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type", kind) != kind:
            raise ValueError(f"decision answer {name} has the wrong type")
        if kind == "noul":
            _number(answer.get("noul"), 0, 1, name)
            continue
        if kind == "choice":
            keys = set(question["criteria"])
            if answer.get("choice") not in keys:
                raise ValueError(f"decision answer {name} selected an unsubmitted option")
            _number(answer.get("confidence"), 0, 1, name + ".confidence")
        elif kind == "score":
            levels = len(question["criteria"])
            if not 2 <= levels <= 10:
                raise ValueError("decision score requires 2 to 10 ordered levels")
            keys = {str(i) for i in range(levels)}
            _number(answer.get("score"), 0, levels - 1, name + ".score")
            if "confidence" in answer:
                _number(answer["confidence"], 0, 1, name + ".confidence")
        else:
            raise ValueError(f"unsupported decision question type {kind}")
        if "probabilities" in answer:
            probabilities = answer["probabilities"]
            if not isinstance(probabilities, dict) or set(probabilities) != keys:
                raise ValueError(
                    f"decision answer {name} probabilities have foreign or missing options"
                )
            for key, value in probabilities.items():
                _number(value, 0, 1, name + ".probabilities." + key)
            if not math.isclose(
                sum(probabilities.values()),
                1,
                abs_tol=PROBABILITY_TOLERANCE + len(probabilities) * rounding_error,
            ):
                raise ValueError(f"decision answer {name} probabilities are not normalized")
            if kind == "choice" and not math.isclose(
                probabilities[answer["choice"]],
                answer["confidence"],
                abs_tol=PROBABILITY_TOLERANCE + 2 * rounding_error,
            ):
                raise ValueError(
                    f"decision answer {name} confidence disagrees with chosen probability"
                )
            if kind == "score" and not math.isclose(
                sum(int(key) * value for key, value in probabilities.items()),
                answer["score"],
                abs_tol=PROBABILITY_TOLERANCE
                + (1 + sum(int(key) for key in keys)) * rounding_error,
            ):
                raise ValueError(f"decision answer {name} score is not its expected level")
    return answers
