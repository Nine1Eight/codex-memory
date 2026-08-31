from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from world.state import GameFingerprint, GameIdentity, clamp01


@dataclass(slots=True)
class SemanticPrior:
    identity: GameIdentity
    family: dict[str, float]
    detectors: dict[str, float]
    controls: dict[str, float]
    topology: dict[str, float]
    interactions: dict[str, float]
    goals: dict[str, float]
    temporal: dict[str, float]
    evidence_count: int = 0


class SemanticIDDecoder:
    """Learns ID/fingerprint associations; never assigns undocumented fixed meanings."""

    def __init__(self, learned: dict[str, dict[str, float]] | None = None) -> None:
        self.learned = learned or {}

    def infer(self, game_id: str, fingerprint: GameFingerprint | None = None) -> SemanticPrior:
        identity = GameIdentity.parse(game_id)
        keys = [f"full:{identity.full_id}", f"base:{identity.base_id}", f"prefix:{identity.prefix}"]
        if fingerprint:
            keys.append(f"fingerprint:{fingerprint.digest}")
        aggregate: dict[str, float] = {}
        counts: dict[str, int] = {}
        for key in keys:
            for label, value in self.learned.get(key, {}).items():
                aggregate[label] = aggregate.get(label, 0.0) + float(value)
                counts[label] = counts.get(label, 0) + 1
        normalized = {key: clamp01(value / counts[key]) for key, value in aggregate.items()}
        group = lambda prefix: {k.split(":", 1)[1]: v for k, v in normalized.items() if k.startswith(prefix + ":")}
        return SemanticPrior(identity, group("family"), group("detector"), group("control"), group("topology"), group("interaction"), group("goal"), group("temporal"), sum(counts.values()))

    def update(self, prior: SemanticPrior, fingerprint: GameFingerprint, observations: dict[str, float]) -> None:
        # Real observation has four times the weight of inherited ID evidence.
        for key in (f"full:{prior.identity.full_id}", f"base:{prior.identity.base_id}", f"prefix:{prior.identity.prefix}", f"fingerprint:{fingerprint.digest}"):
            row = self.learned.setdefault(key, {})
            for label, observed in observations.items():
                row[label] = clamp01(0.2 * row.get(label, 0.5) + 0.8 * observed)
