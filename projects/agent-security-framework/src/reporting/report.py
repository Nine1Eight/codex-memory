"""Deterministic JSON and Markdown reports."""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.models.canonical import canonical_json, stable_hash
from src.search.engine import SearchArchive, SearchResult


class Reporter:
    def build(
        self,
        results: list[SearchResult],
        archive: SearchArchive,
        causal_graphs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        path_lengths = [len(result.actions) for result in results]
        rejected = Counter(
            "non_replayable"
            for result in results
            if not any(f.reproducible for f in result.findings)
        )
        report = {
            "summary": {
                "findings": len(results),
                "unique_states": len(archive.states),
                "transitions": len(archive.transitions),
            },
            "coverage_history": sorted(archive.states),
            "strategy_comparison": dict(
                sorted(Counter(result.strategy for result in results).items())
            ),
            "finding_categories": dict(
                sorted(Counter(f.rule_id for r in results for f in r.findings).items())
            ),
            "replay_reliability": sum(
                any(f.reproducible for f in result.findings) for result in results
            ),
            "path_length_distribution": dict(sorted(Counter(path_lengths).items())),
            "resource_consumption": {"evaluated_results": len(results)},
            "rejected_reasons": dict(sorted(rejected.items())),
            "causal_graphs": causal_graphs or [],
        }
        report["reproducibility_manifest"] = {
            "report_sha256": stable_hash(report),
            "version": "0.1.0",
        }
        return report

    def json(self, report: dict[str, Any]) -> str:
        return canonical_json(report) + "\n"

    def markdown(self, report: dict[str, Any]) -> str:
        summary = report["summary"]
        return (
            "# Synthetic Agent Security Report\n\n"
            f"- Findings: {summary['findings']}\n"
            f"- Unique states: {summary['unique_states']}\n"
            f"- Tool transitions: {summary['transitions']}\n"
            f"- Replay-confirmed: {report['replay_reliability']}\n"
            f"- Manifest: `{report['reproducibility_manifest']['report_sha256']}`\n"
        )
