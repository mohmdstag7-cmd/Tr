"""Per-signal decision traces."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class DecisionStep:
    name: str
    value: Any
    threshold: Any | None = None
    passed: bool | None = None
    ms: float = 0.0


@dataclass
class DecisionTrace:
    signal_id: str
    steps: list[DecisionStep] = field(default_factory=list)
    final_decision: str = "REJECTED"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DecisionTraceStore:
    """In-memory + on-disk persistence."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path("decision_traces")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, DecisionTrace] = {}

    def add_step(self, signal_id: str, step: DecisionStep) -> None:
        trace = self._memory.get(signal_id)
        if trace is None:
            # Try load from disk
            trace = self.get(signal_id)
            if trace is None:
                trace = DecisionTrace(signal_id=signal_id, steps=[], final_decision="REJECTED")
            self._memory[signal_id] = trace
        trace.steps.append(step)
        self._persist(trace)

    def finalize(self, signal_id: str, final_decision: str) -> None:
        trace = self._memory.get(signal_id)
        if trace is None:
            trace = self.get(signal_id)
            if trace is None:
                trace = DecisionTrace(signal_id=signal_id, steps=[], final_decision=final_decision)
            self._memory[signal_id] = trace
        trace.final_decision = final_decision
        self._persist(trace)

    def get(self, signal_id: str) -> DecisionTrace | None:
        if signal_id in self._memory:
            return self._memory[signal_id]
        path = self.base_dir / f"{signal_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            steps = [DecisionStep(**s) for s in data.get("steps", [])]
            created_at_str = data.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except Exception:
                    created_at = datetime.now(UTC)
            else:
                created_at = datetime.now(UTC)
            trace = DecisionTrace(
                signal_id=data["signal_id"],
                steps=steps,
                final_decision=data.get("final_decision", "REJECTED"),
                created_at=created_at,
            )
            self._memory[signal_id] = trace
            return trace
        except Exception:
            return None

    def recent(self, limit: int = 50) -> list[DecisionTrace]:
        # Load from memory and disk
        traces: dict[str, DecisionTrace] = dict(self._memory)
        try:
            for p in self.base_dir.glob("*.json"):
                sid = p.stem
                if sid not in traces:
                    t = self.get(sid)
                    if t is not None:
                        traces[sid] = t
        except Exception:
            pass
        sorted_traces = sorted(traces.values(), key=lambda t: t.created_at, reverse=True)
        return sorted_traces[:limit]

    def _persist(self, trace: DecisionTrace) -> None:
        path = self.base_dir / f"{trace.signal_id}.json"
        try:
            data = {
                "signal_id": trace.signal_id,
                "steps": [asdict(s) for s in trace.steps],
                "final_decision": trace.final_decision,
                "created_at": trace.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


# Module-level store
decision_trace_store = DecisionTraceStore()


def render_decision_trace(trace: DecisionTrace) -> str:
    """Return readable checklist string."""
    parts: list[str] = []
    for step in trace.steps:
        status = "✓" if step.passed else "✗" if step.passed is False else "?"
        if step.threshold is not None:
            # Try to show operator
            if isinstance(step.value, int | float) and isinstance(step.threshold, int | float):
                # Heuristic: if value >= threshold and passed, use ≥ else ≤
                # For failing case, still show expected operator based on passed?
                # Use ≥ if threshold is lower than value or passed implies ≥
                # Simpler: use vs
                # But spec example uses ≥ and ≤, so we try to infer
                if step.passed is True:
                    op = "≥" if step.value >= step.threshold else "≤"
                elif step.passed is False:
                    # Show what was expected: if value < threshold, expected was ≥
                    # We don't know, so use vs
                    op = "≥" if "prob" in step.name.lower() else "≤" if "spread" in step.name.lower() else "vs"
                    # Fallback to vs if unknown
                    if op == "vs":
                        parts.append(f"{step.name} {step.value} vs {step.threshold} {status}")
                        continue
                else:
                    op = "vs"
                if op == "vs":
                    parts.append(f"{step.name} {step.value} vs {step.threshold} {status}")
                else:
                    parts.append(f"{step.name} {step.value} {op} {step.threshold} {status}")
            else:
                parts.append(f"{step.name} {step.value} vs {step.threshold} {status}")
        else:
            parts.append(f"{step.name} {step.value} {status}")
    checklist = " | ".join(parts)
    if checklist:
        return f"{checklist} → {trace.final_decision}"
    return f"→ {trace.final_decision}"
