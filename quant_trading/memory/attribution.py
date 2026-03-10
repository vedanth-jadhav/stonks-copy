from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AttributionRecord:
    signal_score: float
    directionally_correct: bool
    was_decisive: bool
    vindicated: bool
    responsibility: str


def _is_directionally_correct(signal: float, outcome: float) -> bool:
    if abs(signal) < 0.1:
        return True
    if outcome == 0:
        return abs(signal) < 0.25
    return (signal > 0 and outcome > 0) or (signal < 0 and outcome < 0)


def _classify_responsibility(correct: bool, decisive: bool, outcome: float) -> str:
    if outcome > 0:
        if correct and decisive:
            return "PRIMARY_WIN_DRIVER"
        if correct:
            return "SUPPORTING_WIN"
        return "DRAG_ON_WIN"

    if outcome < 0:
        if not correct and decisive:
            return "PRIMARY_LOSS_CAUSE"
        if not correct:
            return "CONTRIBUTING_LOSS"
        if decisive:
            return "VINDICATED_DECISIVE"
        return "VINDICATED_SUPPORTING"

    if decisive:
        return "DECISIVE_NEUTRAL"
    return "NEUTRAL"


def find_root_cause(attribution: dict[str, AttributionRecord]) -> str:
    for agent_id, record in attribution.items():
        if record.responsibility == "PRIMARY_LOSS_CAUSE":
            return f"AGENT_FAILURE:{agent_id}"
    decisive_negative = [
        agent_id
        for agent_id, record in attribution.items()
        if record.was_decisive and not record.directionally_correct
    ]
    if decisive_negative:
        return f"MULTI_AGENT_FAILURE:{','.join(sorted(decisive_negative))}"
    return "EXTERNAL_EVENT_OR_TIMING"


def attribute_trade_outcome(
    conviction_threshold: float,
    signals: dict[str, float],
    outcome: float,
) -> dict[str, dict[str, Any]]:
    total_conviction = sum(signals.values())
    attribution: dict[str, AttributionRecord] = {}

    for agent_id, signal in signals.items():
        directionally_correct = _is_directionally_correct(signal=signal, outcome=outcome)
        counterfactual_conviction = total_conviction - signal
        was_decisive = (total_conviction >= conviction_threshold) != (
            counterfactual_conviction >= conviction_threshold
        )
        vindicated = directionally_correct and outcome < 0
        attribution[agent_id] = AttributionRecord(
            signal_score=signal,
            directionally_correct=directionally_correct,
            was_decisive=was_decisive,
            vindicated=vindicated,
            responsibility=_classify_responsibility(directionally_correct, was_decisive, outcome),
        )

    root_cause = find_root_cause(attribution)
    return {
        agent_id: {
            "signal_score": record.signal_score,
            "directionally_correct": record.directionally_correct,
            "was_decisive": record.was_decisive,
            "vindicated": record.vindicated,
            "responsibility": record.responsibility,
            "root_cause": root_cause,
        }
        for agent_id, record in attribution.items()
    }
