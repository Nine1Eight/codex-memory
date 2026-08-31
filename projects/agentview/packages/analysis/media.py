from __future__ import annotations

from dataclasses import dataclass, asdict, is_dataclass
from enum import Enum
from pathlib import Path
import hashlib
import json
import re
from typing import Any

from PIL import Image, ImageSequence, ImageOps

from packages.domain import (
    AuthorityDecision,
    Claim,
    Coverage,
    DeduplicationKeyInput,
    EvidenceScore,
    LocalSigner,
    ReceiptPayload,
    ReceiptSignature,
    ScoreBreakdown,
    ViewClass,
    canonical_json,
    compute_claim_merkle_root,
    compute_deduplication_key,
    qualify_view,
    round2,
)


@dataclass(frozen=True)
class AnalysisResult:
    receipt_payload: ReceiptPayload
    receipt_signature: ReceiptSignature
    transcript_excerpt: str
    frame_texts: tuple[str, ...]
    claims: tuple[Claim, ...]
    summary: str


def _ocr(image: Image.Image) -> str:
    try:
        import pytesseract  # type: ignore
        return (pytesseract.image_to_string(image, config='--psm 6') or '').strip()
    except Exception:
        return ''


def _sample_frames(video_path: Path, max_frames: int = 8) -> list[tuple[int, str]]:
    image = Image.open(video_path)
    frames = list(ImageSequence.Iterator(image))
    if not frames:
        raise ValueError('unable to open video')
    sampled: list[tuple[int, str]] = []
    step = max(1, len(frames) // max_frames)
    for index, frame in enumerate(frames[::step][:max_frames]):
        rgb = ImageOps.exif_transpose(frame).convert('RGB')
        sampled.append((index, _ocr(rgb)))
    return sampled


def _extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r'[A-Za-z0-9][A-Za-z0-9_-]{2,}', text.lower())
    stop = {'the', 'and', 'with', 'that', 'this', 'from', 'video', 'agentview', 'for', 'you'}
    unique: list[str] = []
    for token in tokens:
        if token in stop or token in unique:
            continue
        unique.append(token)
    return unique[:12]


def _build_claims(frame_texts: list[tuple[int, str]], transcript: str) -> list[Claim]:
    transcript_keywords = _extract_keywords(transcript)
    claims: list[Claim] = []
    for idx, (second, frame_text) in enumerate(frame_texts, start=1):
        keywords = _extract_keywords(frame_text)
        if not keywords:
            continue
        overlap = [word for word in keywords if word in transcript_keywords]
        proposition = f"At {second}s the video shows {' '.join(keywords[:3])}".strip()
        if overlap:
            proposition = f"At {second}s the video shows {' '.join(overlap[:3])} supported by the transcript"
        claims.append(
            Claim(
                claim_id=f'claim-{idx}',
                normalized_proposition=proposition,
                importance=3,
                stance='asserted',
                evidence_refs=(f'frame:{second}',),
                support=1.0 if overlap or frame_text else 0.75,
                contradiction=0.0,
                confidence=0.8 if overlap else 0.65,
            )
        )
    if transcript_keywords:
        claims.append(
            Claim(
                claim_id=f'claim-{len(claims) + 1}',
                normalized_proposition=f"The transcript discusses {' '.join(transcript_keywords[:5])}",
                importance=2,
                stance='asserted',
                evidence_refs=('transcript',),
                support=1.0,
                contradiction=0.0,
                confidence=0.85,
            )
        )
    return claims


def _receipt_payload_plain(payload: ReceiptPayload) -> dict[str, Any]:
    def plain(value: Any) -> Any:
        if is_dataclass(value):
            return {key: plain(item) for key, item in asdict(value).items()}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(item) for item in value]
        return value

    return plain(payload)


def analyze_video_file(
    *,
    tenant_id: str,
    agent_id: str,
    agent_version_id: str,
    source_id: str,
    source_revision_id: str,
    source_fingerprint_sha256: str,
    source_type: str,
    authority_class: str,
    objective_id: str,
    objective_type: str,
    job_id: str,
    video_path: Path,
    transcript: str,
    delegation_mode: str = 'human_delegated',
    policy_version: str = '1.0.0',
    evidence_policy_version: str = '1.0.0',
) -> AnalysisResult:
    frame_texts = _sample_frames(video_path)
    transcript_keywords = _extract_keywords(transcript)
    claims = _build_claims(frame_texts, transcript)
    if not claims:
        claims = [
            Claim(
                claim_id='claim-1',
                normalized_proposition='The uploaded media contains at least one observable frame and/or transcript segment.',
                importance=1,
                stance='asserted',
                evidence_refs=('frame:0',),
                support=0.6,
                contradiction=0.0,
                confidence=0.5,
            )
        ]
    coverage = Coverage(
        required=1.0,
        audio=0.0,
        transcript=1.0 if transcript.strip() else 0.0,
        visual=min(1.0, len(frame_texts) / 4.0),
    ).clamp()
    evidence_alignment = round2(sum(claim.support * claim.importance for claim in claims) / sum(claim.importance for claim in claims))
    comprehension = round2(min(1.0, 0.5 + 0.1 * len(_extract_keywords(transcript))))
    consistency = round2(1.0 - min(0.2, sum(1 for claim in claims if claim.contradiction > 0) * 0.05))
    outcome = 1.0
    qualified, vcs = qualify_view(
        ViewClass.MULTIMODAL,
        AuthorityDecision.ALLOW,
        coverage,
        evidence_alignment,
        comprehension,
        consistency,
        outcome,
        False,
        (),
    )
    claims_root = compute_claim_merkle_root(claims)
    dedupe_key = compute_deduplication_key(
        DeduplicationKeyInput(
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            source_revision_fingerprint=source_fingerprint_sha256,
            objective_canonical_sha256=hashlib.sha256(canonical_json({'objective_id': objective_id, 'objective_type': objective_type}).encode('utf-8')).hexdigest(),
            evidence_policy_version=evidence_policy_version,
        )
    )
    frame_keywords = sorted({word for _, text in frame_texts for word in _extract_keywords(text)})
    summary = ' '.join(frame_keywords or transcript_keywords) or 'Video processed.'
    payload = ReceiptPayload(
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_version_id=agent_version_id,
        key_id='local-dev-key',
        source_id=source_id,
        source_revision_id=source_revision_id,
        source_type=source_type,
        source_fingerprint_sha256=source_fingerprint_sha256,
        external_reference=None,
        duration_ms=max((second for second, _ in frame_texts), default=0) * 1000,
        language_codes=('en',),
        authority_class=authority_class,
        authority_decision='allow',
        policy_version=policy_version,
        objective_id=objective_id,
        objective_type=objective_type,
        canonical_sha256=hashlib.sha256(canonical_json({'summary': summary, 'claims': [claim.normalized_proposition for claim in claims]}).encode('utf-8')).hexdigest(),
        job_id=job_id,
        delegation_mode=delegation_mode,
        started_at='2026-08-14T00:00:00.000Z',
        completed_at='2026-08-14T00:00:00.000Z',
        attempt_count=1,
        view_class=ViewClass.MULTIMODAL,
        qualified=qualified,
        qualification_failures=(),
        coverage=coverage,
        scores=ScoreBreakdown(
            coverage=coverage,
            evidence=EvidenceScore(evidence_alignment=evidence_alignment, comprehension=comprehension, consistency=consistency, outcome=outcome),
            viewing_confidence=vcs,
        ),
        claims_count=len(claims),
        material_claim_count=len(claims),
        claims_merkle_root_sha256=claims_root,
        outcome_id='outcome-1',
        outcome_schema_id='agentview.outcome.simple.v1',
        outcome_content_sha256=hashlib.sha256(summary.encode('utf-8')).hexdigest(),
        content_merit=None,
        deduplication_key_sha256=dedupe_key,
        created_at='2026-08-14T00:00:00.000Z',
    )
    signer = LocalSigner('local-dev-key', b'agentview-local-dev-secret')
    signature = signer.sign(_receipt_payload_plain(payload))
    return AnalysisResult(
        receipt_payload=payload,
        receipt_signature=signature,
        transcript_excerpt=transcript[:2000],
        frame_texts=tuple(text for _, text in frame_texts),
        claims=tuple(claims),
        summary=summary,
    )
