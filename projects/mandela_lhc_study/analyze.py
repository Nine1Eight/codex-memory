#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

BASE = Path.home() / "mandela_lhc_study"
DATA = BASE / "data"
OUT = BASE / "out"

def parse_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()

@dataclass
class LHCWindow:
    window_id: str
    name: str
    start: date
    end: date
    type: str
    intensity: float
    source: str

@dataclass
class MandelaEvent:
    event_id: str
    name: str
    claimed_memory: str
    archive_version: str
    first_public_notice: Optional[date]
    source: str
    confidence: float
    category: str

def read_lhc() -> List[LHCWindow]:
    rows = []
    with open(DATA / "lhc_windows.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(LHCWindow(
                window_id=r["window_id"],
                name=r["name"],
                start=parse_date(r["start_date"]),
                end=parse_date(r["end_date"]),
                type=r["type"],
                intensity=float(r["intensity_score"]),
                source=r["source"],
            ))
    return rows

def read_mandela() -> List[MandelaEvent]:
    rows = []
    with open(DATA / "mandela_events.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(MandelaEvent(
                event_id=r["event_id"],
                name=r["name"],
                claimed_memory=r["claimed_memory"],
                archive_version=r["archive_version"],
                first_public_notice=parse_date(r["first_public_notice_date"]),
                source=r["first_notice_source"],
                confidence=float(r["confidence_0_1"] or 0.0),
                category=r["category"],
            ))
    return rows

def nearest_prior_window(d: date, windows: List[LHCWindow]) -> Optional[Tuple[LHCWindow, int]]:
    candidates = []
    for w in windows:
        if w.end <= d:
            lag = (d - w.end).days
            candidates.append((w, lag))
    if not candidates:
        return None
    return min(candidates, key=lambda x: x[1])

def proximity_score(lag_days: Optional[int]) -> float:
    if lag_days is None:
        return 0.0
    # exponential decay, half-life about 180 days
    return math.exp(-lag_days / 180.0)

def classify_lag(lag: Optional[int]) -> str:
    if lag is None:
        return "no_prior_lhc_window"
    if lag <= 30:
        return "strong_0_30_days"
    if lag <= 180:
        return "medium_31_180_days"
    if lag <= 365:
        return "weak_181_365_days"
    return "distant_366_plus_days"

def monte_carlo(events: List[MandelaEvent], windows: List[LHCWindow], trials: int = 5000) -> dict:
    observed_dates = [e.first_public_notice for e in events if e.first_public_notice]
    if not observed_dates:
        return {"error": "No dated Mandela events yet."}

    start = min(w.start for w in windows)
    end = max(max(observed_dates), max(w.end for w in windows)) + timedelta(days=365)
    span = (end - start).days

    def total_score(dates: List[date]) -> float:
        s = 0.0
        for d in dates:
            p = nearest_prior_window(d, windows)
            lag = p[1] if p else None
            s += proximity_score(lag)
        return s

    observed = total_score(observed_dates)
    ge = 0
    random_scores = []

    for _ in range(trials):
        rand_dates = [start + timedelta(days=random.randint(0, span)) for _ in observed_dates]
        rs = total_score(rand_dates)
        random_scores.append(rs)
        if rs >= observed:
            ge += 1

    p_value = (ge + 1) / (trials + 1)
    random_scores.sort()

    return {
        "observed_score": observed,
        "random_median": random_scores[len(random_scores)//2],
        "random_95th": random_scores[int(len(random_scores)*0.95)],
        "p_value": p_value,
        "trials": trials,
    }

def main() -> None:
    OUT.mkdir(exist_ok=True)
    windows = read_lhc()
    events = read_mandela()

    report_rows = []
    for e in events:
        if not e.first_public_notice:
            report_rows.append({
                "event_id": e.event_id,
                "name": e.name,
                "first_public_notice": "",
                "nearest_lhc_window": "",
                "lag_days": "",
                "lag_class": "undated_event_needs_research",
                "proximity_score": "",
                "confidence_0_1": e.confidence,
                "source": e.source,
            })
            continue

        prior = nearest_prior_window(e.first_public_notice, windows)
        if prior:
            w, lag = prior
            ps = proximity_score(lag)
            report_rows.append({
                "event_id": e.event_id,
                "name": e.name,
                "first_public_notice": e.first_public_notice.isoformat(),
                "nearest_lhc_window": w.name,
                "lag_days": lag,
                "lag_class": classify_lag(lag),
                "proximity_score": round(ps, 6),
                "confidence_0_1": e.confidence,
                "source": e.source,
            })
        else:
            report_rows.append({
                "event_id": e.event_id,
                "name": e.name,
                "first_public_notice": e.first_public_notice.isoformat(),
                "nearest_lhc_window": "",
                "lag_days": "",
                "lag_class": "no_prior_lhc_window",
                "proximity_score": 0,
                "confidence_0_1": e.confidence,
                "source": e.source,
            })

    out_csv = OUT / "mandela_lhc_lag_report.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        fields = [
            "event_id", "name", "first_public_notice", "nearest_lhc_window",
            "lag_days", "lag_class", "proximity_score", "confidence_0_1", "source"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)

    mc = monte_carlo(events, windows)

    out_txt = OUT / "summary.txt"
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("MANDELA × LHC TIMING STUDY — V1\n")
        f.write("================================\n\n")
        f.write(f"Events loaded: {len(events)}\n")
        f.write(f"LHC windows loaded: {len(windows)}\n\n")
        f.write("Monte Carlo result:\n")
        for k, v in mc.items():
            f.write(f"  {k}: {v}\n")
        f.write("\nInterpretation:\n")
        f.write("  p_value below 0.05 = timing cluster stronger than random baseline.\n")
        f.write("  High p_value = no useful evidence of LHC timing relationship.\n")
        f.write("\nGenerated files:\n")
        f.write(f"  {out_csv}\n")

    print("[DONE] Analysis complete")
    print("[REPORT]", out_csv)
    print("[SUMMARY]", out_txt)

if __name__ == "__main__":
    main()
