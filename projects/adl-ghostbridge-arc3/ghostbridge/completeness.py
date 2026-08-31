from __future__ import annotations

from dataclasses import dataclass

from .schemas import TransitionEnvelope


@dataclass(frozen=True, slots=True)
class CompletenessReport:
    complete: bool
    missing: tuple[str, ...]


class TransitionCompleteness:
    REQUIRED = ("pre_observation", "action", "post_observation", "delta", "events", "assessment", "planner_phase", "hashes")

    def check(self, envelope: TransitionEnvelope) -> CompletenessReport:
        missing = tuple(name for name in self.REQUIRED if getattr(envelope, name, None) in (None, ""))
        try: envelope.verify()
        except Exception as exc: missing += (f"integrity:{exc}",)
        return CompletenessReport(not missing, missing)

