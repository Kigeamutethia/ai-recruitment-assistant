"""Deterministic ranking.

The LLM scores each criterion 0–5 with evidence; this module combines those scores with the
recruiter's weights. Because it's plain Python, it is reproducible, unit-testable, and a change
of weights re-ranks every candidate instantly — no new AI calls.
"""
from dataclasses import dataclass

MAX_CRITERION_SCORE = 5
MUST_HAVE_THRESHOLD = 3  # "meets the requirement" on the 0–5 scale


@dataclass
class ScoreResult:
    overall: float              # 0–100
    must_have_met: bool
    criteria: list[dict]        # per-criterion rows merged with job config


def compute_score(job_criteria: list[dict], criterion_scores: list[dict]) -> ScoreResult:
    by_key = {c["key"]: c for c in criterion_scores}
    rows, weighted, total_weight, must_have_met = [], 0.0, 0.0, True

    for crit in job_criteria:
        assessed = by_key.get(crit["key"])
        score = max(0, min(MAX_CRITERION_SCORE, int(assessed["score"]))) if assessed else 0
        weight = float(crit.get("weight", 1))
        weighted += weight * score
        total_weight += weight
        if crit.get("must_have") and score < MUST_HAVE_THRESHOLD:
            must_have_met = False
        rows.append({
            "key": crit["key"],
            "label": crit["label"],
            "weight": weight,
            "must_have": bool(crit.get("must_have")),
            "score": score,
            "assessed": assessed is not None,
            "evidence": assessed.get("evidence", []) if assessed else [],
            "reasoning": assessed.get("reasoning", "") if assessed
            else "Criterion added after this assessment — re-analyse to score it.",
        })

    overall = round(100 * weighted / (total_weight * MAX_CRITERION_SCORE), 2) if total_weight else 0.0
    return ScoreResult(overall=overall, must_have_met=must_have_met, criteria=rows)
