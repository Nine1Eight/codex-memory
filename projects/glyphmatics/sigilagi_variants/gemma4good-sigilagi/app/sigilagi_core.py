#!/usr/bin/env python3
"""
SigilAGI Core Engine

Purpose:
Convert detected objects into glyph mappings, symbolic scene traces,
and plain-language reasoning reports.

This version is dependency-free and works in Termux.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List


GLYPH_MAP: Dict[str, Dict[str, str]] = {
    "person": {
        "glyph": "☉",
        "meaning": "actor / observer / intent",
        "role": "human subject",
        "risk": "human-review"
    },
    "human": {
        "glyph": "☉",
        "meaning": "actor / observer / intent",
        "role": "human subject",
        "risk": "human-review"
    },
    "face": {
        "glyph": "◉",
        "meaning": "identity-sensitive visual feature",
        "role": "privacy-sensitive feature",
        "risk": "privacy-review"
    },
    "door": {
        "glyph": "⛩",
        "meaning": "boundary / transition / access",
        "role": "entry or exit point",
        "risk": "low"
    },
    "window": {
        "glyph": "▤",
        "meaning": "visibility / opening / observation",
        "role": "viewpoint or opening",
        "risk": "low"
    },
    "phone": {
        "glyph": "☏",
        "meaning": "communication / signal / record",
        "role": "information device",
        "risk": "low"
    },
    "camera": {
        "glyph": "◈",
        "meaning": "recording / observation / evidence",
        "role": "capture device",
        "risk": "privacy-review"
    },
    "car": {
        "glyph": "⟡",
        "meaning": "movement / transport / force",
        "role": "vehicle",
        "risk": "medium"
    },
    "truck": {
        "glyph": "⟡",
        "meaning": "movement / transport / force",
        "role": "vehicle",
        "risk": "medium"
    },
    "vehicle": {
        "glyph": "⟡",
        "meaning": "movement / transport / force",
        "role": "vehicle",
        "risk": "medium"
    },
    "bag": {
        "glyph": "▣",
        "meaning": "container / carried item / storage",
        "role": "portable container",
        "risk": "low"
    },
    "backpack": {
        "glyph": "▣",
        "meaning": "container / carried item / storage",
        "role": "portable container",
        "risk": "low"
    },
    "light": {
        "glyph": "✦",
        "meaning": "visibility / signal / attention",
        "role": "illumination or signal",
        "risk": "low"
    },
    "knife": {
        "glyph": "⚠",
        "meaning": "possible danger / sharp object / review required",
        "role": "hazard object",
        "risk": "high-review"
    },
    "gun": {
        "glyph": "⚠",
        "meaning": "possible weapon / danger / review required",
        "role": "hazard object",
        "risk": "high-review"
    },
    "weapon": {
        "glyph": "⚠",
        "meaning": "possible danger / review required",
        "role": "hazard object",
        "risk": "high-review"
    },
    "dog": {
        "glyph": "♞",
        "meaning": "animal / movement / alertness",
        "role": "animal subject",
        "risk": "medium"
    },
    "cat": {
        "glyph": "♘",
        "meaning": "animal / movement / presence",
        "role": "animal subject",
        "risk": "low"
    },
    "paper": {
        "glyph": "▧",
        "meaning": "document / record / instruction",
        "role": "written evidence",
        "risk": "low"
    },
    "document": {
        "glyph": "▧",
        "meaning": "document / record / instruction",
        "role": "written evidence",
        "risk": "low"
    },
    "money": {
        "glyph": "¤",
        "meaning": "value / transaction / resource",
        "role": "financial object",
        "risk": "medium"
    },
    "wallet": {
        "glyph": "▨",
        "meaning": "identity / value / personal property",
        "role": "personal property",
        "risk": "privacy-review"
    },
    "key": {
        "glyph": "⌘",
        "meaning": "access / permission / control",
        "role": "access object",
        "risk": "medium"
    }
}


DEFAULT_GLYPH = {
    "glyph": "◇",
    "meaning": "unknown object / unmapped symbol",
    "role": "unclassified object",
    "risk": "unknown"
}


def normalize_label(label: str) -> str:
    cleaned = label.strip().lower()
    cleaned = re.sub(r"[^a-z0-9 _-]", "", cleaned)
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def parse_labels(raw: str) -> List[str]:
    parts = re.split(r"[,;\n]+", raw)
    labels = []
    for part in parts:
        label = normalize_label(part)
        if label:
            labels.append(label)
    return labels


def map_object_to_glyph(label: str, index: int) -> Dict[str, Any]:
    normalized = normalize_label(label)
    mapping = GLYPH_MAP.get(normalized, DEFAULT_GLYPH)

    return {
        "index": index,
        "label": normalized,
        "glyph": mapping["glyph"],
        "meaning": mapping["meaning"],
        "role": mapping["role"],
        "risk": mapping["risk"],
        "detection_source": "user_label_or_detector_output"
    }


def build_glyph_summary(glyph_objects: List[Dict[str, Any]]) -> str:
    if not glyph_objects:
        return ""

    glyphs = [item["glyph"] for item in glyph_objects]

    if len(glyphs) == 1:
        return glyphs[0]

    return " → ".join(glyphs)


def build_relationships(glyph_objects: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    relationships = []

    labels = [item["label"] for item in glyph_objects]

    has_person = "person" in labels or "human" in labels
    has_phone = "phone" in labels
    has_door = "door" in labels
    has_vehicle = any(label in labels for label in ["car", "truck", "vehicle"])
    has_hazard = any(item["risk"] == "high-review" for item in glyph_objects)

    if has_person and has_phone:
        relationships.append({
            "symbolic": "☉ near ☏",
            "plain": "A human subject and a communication or recording device appear in the same scene."
        })

    if has_person and has_door:
        relationships.append({
            "symbolic": "☉ near ⛩",
            "plain": "A human subject and an access boundary appear in the same scene."
        })

    if has_person and has_vehicle:
        relationships.append({
            "symbolic": "☉ near ⟡",
            "plain": "A human subject and a vehicle or movement object appear in the same scene."
        })

    if has_hazard:
        relationships.append({
            "symbolic": "⚠ requires review",
            "plain": "A potentially hazardous object label is present and should be reviewed by a human."
        })

    return relationships


def build_plain_summary(glyph_objects: List[Dict[str, Any]], relationships: List[Dict[str, str]]) -> str:
    if not glyph_objects:
        return "No objects were provided for glyph conversion."

    object_phrase = ", ".join(item["label"] for item in glyph_objects)

    if relationships:
        relation_phrase = " ".join(rel["plain"] for rel in relationships)
        return f"The scene contains: {object_phrase}. {relation_phrase}"

    return f"The scene contains: {object_phrase}. These objects were converted into glyph symbols for structured reasoning."


def build_risk_flags(glyph_objects: List[Dict[str, Any]]) -> List[str]:
    flags = []

    for item in glyph_objects:
        risk = item["risk"]

        if risk == "high-review":
            flags.append(f"High-review object detected: {item['label']} mapped to {item['glyph']}.")

        if risk == "privacy-review":
            flags.append(f"Privacy-sensitive object detected: {item['label']} mapped to {item['glyph']}.")

        if risk == "unknown":
            flags.append(f"Unknown object mapping: {item['label']} mapped to default glyph {item['glyph']}.")

    return flags


def build_unknowns(glyph_objects: List[Dict[str, Any]]) -> List[str]:
    unknowns = [
        "The system cannot verify identity, intent, guilt, legality, medical status, or exact danger level from object labels alone.",
        "Object labels may be incomplete or incorrect if provided manually or by a detector.",
        "Spatial relationships are approximate unless bounding boxes or coordinates are supplied."
    ]

    if any(item["risk"] == "unknown" for item in glyph_objects):
        unknowns.append("One or more objects used the default unmapped glyph and need a custom mapping.")

    return unknowns


def generate_report(raw_labels: str, scene_note: str = "") -> Dict[str, Any]:
    labels = parse_labels(raw_labels)
    glyph_objects = [map_object_to_glyph(label, index=i) for i, label in enumerate(labels, start=1)]
    relationships = build_relationships(glyph_objects)
    glyph_summary = build_glyph_summary(glyph_objects)
    plain_summary = build_plain_summary(glyph_objects, relationships)

    report = {
        "project": "SigilAGI",
        "mode": "object_to_glyph_detection",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scene_note": scene_note.strip(),
        "detected_objects": labels,
        "glyph_objects": glyph_objects,
        "glyph_summary": glyph_summary,
        "relationships": relationships,
        "plain_english_summary": plain_summary,
        "risk_flags": build_risk_flags(glyph_objects),
        "unknowns": build_unknowns(glyph_objects),
        "human_review_needed": [
            "Review any privacy-sensitive or high-risk glyphs before using the report.",
            "Do not treat symbolic output as proof. Treat it as an organized reasoning trace."
        ]
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="SigilAGI object-to-glyph detection engine")
    parser.add_argument(
        "--labels",
        required=True,
        help="Comma-separated object labels, example: 'person, phone, door'"
    )
    parser.add_argument(
        "--note",
        default="",
        help="Optional scene note"
    )

    args = parser.parse_args()
    report = generate_report(args.labels, args.note)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
