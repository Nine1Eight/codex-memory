from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from packages.analysis.media import AnalysisResult
from packages.domain import (
    AuthorityDecision,
    Claim,
    Coverage,
    EvidenceScore,
    DeduplicationKeyInput,
    LocalSigner,
    ReceiptPayload,
    ScoreBreakdown,
    ViewClass,
    canonical_json,
    compute_claim_merkle_root,
    compute_deduplication_key,
    round2,
)


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _make_video(path: Path, labels: list[str]) -> None:
    frames = []
    for text in labels:
        image = Image.new("RGB", (320, 240), "black")
        draw = ImageDraw.Draw(image)
        draw.text((30, 120), text, fill="white")
        frames.append(image)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=1000, loop=0)


def _reload_app(tmp_path: Path):
    os.environ["AGENTVIEW_DATABASE_PATH"] = str(tmp_path / "agentview.sqlite3")
    os.environ["AGENTVIEW_BOOTSTRAP_THRESHOLD"] = "2"
    for module in [
        "agentview_api.main",
        "agentview_api.app",
        "agentview_api.dependencies",
    ]:
        sys.modules.pop(module, None)
    import agentview_api.dependencies as dependencies
    import agentview_api.app as app_module
    import agentview_api.main as main_module

    return app_module, dependencies


def _claims() -> tuple[Claim, ...]:
    return (
        Claim(
            claim_id="claim-1",
            normalized_proposition="The media mentions AgentView bootstrap evidence.",
            importance=1,
            stance="asserted",
            evidence_refs=("frame:0",),
            support=1.0,
            contradiction=0.0,
            confidence=1.0,
        ),
    )


def _qualified_result(
    *,
    tenant_id: str,
    source_id: str,
    source_revision_id: str,
    source_fingerprint_sha256: str,
    objective_type: str,
    view_class: ViewClass = ViewClass.MULTIMODAL,
    qualified: bool = True,
) -> AnalysisResult:
    claims = _claims()
    payload = ReceiptPayload(
        tenant_id=tenant_id,
        agent_id="agent-1",
        agent_version_id="agent-version-1",
        key_id="local-dev-key",
        source_id=source_id,
        source_revision_id=source_revision_id,
        source_type="uploaded_media",
        source_fingerprint_sha256=source_fingerprint_sha256,
        external_reference=None,
        duration_ms=1000,
        language_codes=("en",),
        authority_class="owned_media",
        authority_decision=AuthorityDecision.ALLOW.value,
        policy_version="1.0.0",
        objective_id="objective-1",
        objective_type=objective_type,
        canonical_sha256=hashlib.sha256(canonical_json({"objective": objective_type}).encode("utf-8")).hexdigest(),
        job_id="job-1",
        delegation_mode="human_delegated",
        started_at="2026-08-14T00:00:00.000Z",
        completed_at="2026-08-14T00:00:00.000Z",
        attempt_count=1,
        view_class=view_class,
        qualified=qualified,
        qualification_failures=(),
        coverage=Coverage(required=1.0, audio=1.0, transcript=1.0, visual=1.0),
        scores=ScoreBreakdown(
            coverage=Coverage(required=1.0, audio=1.0, transcript=1.0, visual=1.0),
            evidence=EvidenceScore(evidence_alignment=1.0, comprehension=1.0, consistency=1.0, outcome=1.0),
            viewing_confidence=100.0,
        ),
        claims_count=len(claims),
        material_claim_count=len(claims),
        claims_merkle_root_sha256=compute_claim_merkle_root(list(claims)),
        outcome_id="outcome-1",
        outcome_schema_id="agentview.outcome.simple.v1",
        outcome_content_sha256=hashlib.sha256(b"summary").hexdigest(),
        content_merit=None,
        deduplication_key_sha256=compute_deduplication_key(
            DeduplicationKeyInput(
                agent_id="agent-1",
                agent_version_id="agent-version-1",
                source_revision_fingerprint=source_fingerprint_sha256,
                objective_canonical_sha256=hashlib.sha256(
                    canonical_json({"objective": objective_type}).encode("utf-8")
                ).hexdigest(),
                evidence_policy_version="1.0.0",
            )
        ),
        created_at="2026-08-14T00:00:00.000Z",
    )
    signature = LocalSigner("local-dev-key", b"agentview-local-dev-secret").sign(
        {
            "tenant_id": tenant_id,
            "source_id": source_id,
            "source_revision_id": source_revision_id,
            "source_fingerprint_sha256": source_fingerprint_sha256,
        }
    )
    return AnalysisResult(
        receipt_payload=payload,
        receipt_signature=signature,
        transcript_excerpt="agentview bootstrap evidence",
        frame_texts=("AgentView bootstrap evidence",),
        claims=claims,
        summary="AgentView bootstrap evidence",
    )


@pytest.fixture()
def api_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    app_module, dependencies = _reload_app(tmp_path)
    monkeypatch.setattr(dependencies, "store", dependencies.store, raising=False)
    return app_module, dependencies


def test_bootstrap_status_starts_locked(api_runtime) -> None:
    app_module, _ = api_runtime
    client = TestClient(app_module.app)

    body = client.get("/setup/status").json()

    assert body["bootstrap"] == {"count": 0, "threshold": 2, "locked": True}
    assert body["bootstrap_threshold"] == 2


def test_one_qualified_multimodal_view_counts_exactly_once_and_keeps_lock(tmp_path: Path) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    video_path = tmp_path / "sample.gif"
    _make_video(video_path, ["HELLO", "AGENTVIEW"])

    def fake_analyze(**kwargs):
        return _qualified_result(
            tenant_id=kwargs["tenant_id"],
            source_id=kwargs["source_id"],
            source_revision_id=kwargs["source_revision_id"],
            source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
            objective_type=kwargs["objective_type"],
        )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(app_module, "analyze_video_file", fake_analyze)
        with video_path.open("rb") as handle:
            response = client.post(
                "/analyze?objective=comprehensive_summary",
                files={"file": ("sample.gif", handle, "image/gif")},
                data={"transcript": "HELLO AGENTVIEW"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["bootstrap"] == {"count": 1, "threshold": 2, "locked": True}
    assert body["receipt"]["payload"]["qualified"] is True
    assert body["receipt"]["payload"]["view_class"] == "multimodal"

    recommendations = client.get("/recommendations").json()
    assert recommendations == {
        "status": "locked",
        "bootstrap": {"count": 1, "threshold": 2, "locked": True},
        "message": "bootstrap mode requires 2 qualified multimodal views before rankings unlock",
    }


def test_identical_bytes_deduplicate_by_fingerprint_even_with_new_objective_or_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    video_path = tmp_path / "sample.gif"
    _make_video(video_path, ["QUALIFY", "AGAIN"])
    fingerprint = "sha256:" + hashlib.sha256(video_path.read_bytes()).hexdigest()

    def fake_analyze(**kwargs):
        return _qualified_result(
            tenant_id=kwargs["tenant_id"],
            source_id=kwargs["source_id"],
            source_revision_id=kwargs["source_revision_id"],
            source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
            objective_type=kwargs["objective_type"],
        )

    monkeypatch.setattr(app_module, "analyze_video_file", fake_analyze)

    for objective in ("comprehensive_summary", "claim_inventory"):
        with video_path.open("rb") as handle:
            response = client.post(f"/analyze?objective={objective}", files={"file": ("sample.gif", handle, "image/gif")})
        assert response.status_code == 200

    body = client.get("/setup/status").json()
    assert body["bootstrap"] == {"count": 1, "threshold": 2, "locked": True}
    first = client.get("/audit-events").json()["items"]
    assert any(item["action"] == "bootstrap.view.record" for item in first)
    assert fingerprint in {event["resource_id"] for event in first if event["action"] == "bootstrap.view.record"}


@pytest.mark.parametrize(
    "view_class, qualified, transcript, expect_count",
    [
        (ViewClass.MULTIMODAL, False, "VISUAL AUDIO", 0),
        (ViewClass.TRANSCRIPT, False, "ONLY TEXT", 0),
        (ViewClass.VISUAL, False, "", 0),
        (ViewClass.METADATA_OBSERVATION, False, "", 0),
    ],
)
def test_non_qualifying_modes_do_not_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    view_class: ViewClass,
    qualified: bool,
    transcript: str,
    expect_count: int,
) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    video_path = tmp_path / "sample.gif"
    _make_video(video_path, ["X", "Y"])

    def fake_analyze(**kwargs):
        return _qualified_result(
            tenant_id=kwargs["tenant_id"],
            source_id=kwargs["source_id"],
            source_revision_id=kwargs["source_revision_id"],
            source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
            objective_type=kwargs["objective_type"],
            view_class=view_class,
            qualified=qualified,
        )

    monkeypatch.setattr(app_module, "analyze_video_file", fake_analyze)
    with video_path.open("rb") as handle:
        response = client.post(
            "/analyze?objective=comprehensive_summary",
            files={"file": ("sample.gif", handle, "image/gif")},
            data={"transcript": transcript},
        )
    assert response.status_code == 200
    assert response.json()["bootstrap"]["count"] == expect_count


def test_unqualified_first_attempt_does_not_poison_fingerprint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    video_path = tmp_path / "sample.gif"
    _make_video(video_path, ["FIRST", "SECOND"])

    attempts = [False, True]

    def fake_analyze(**kwargs):
        return _qualified_result(
            tenant_id=kwargs["tenant_id"],
            source_id=kwargs["source_id"],
            source_revision_id=kwargs["source_revision_id"],
            source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
            objective_type=kwargs["objective_type"],
            qualified=attempts.pop(0),
        )

    monkeypatch.setattr(app_module, "analyze_video_file", fake_analyze)

    with video_path.open("rb") as handle:
        first = client.post("/analyze?objective=comprehensive_summary", files={"file": ("sample.gif", handle, "image/gif")})
    assert first.json()["bootstrap"] == {"count": 0, "threshold": 2, "locked": True}
    with video_path.open("rb") as handle:
        second = client.post("/analyze?objective=comprehensive_summary", files={"file": ("sample.gif", handle, "image/gif")})
    assert second.json()["bootstrap"] == {"count": 1, "threshold": 2, "locked": True}


def test_second_distinct_qualified_source_unlocks_recommendations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)

    def fake_analyze(**kwargs):
        return _qualified_result(
            tenant_id=kwargs["tenant_id"],
            source_id=kwargs["source_id"],
            source_revision_id=kwargs["source_revision_id"],
            source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
            objective_type=kwargs["objective_type"],
        )

    monkeypatch.setattr(app_module, "analyze_video_file", fake_analyze)
    for labels in (["A"], ["B"]):
        video_path = tmp_path / f"{labels[0]}.gif"
        _make_video(video_path, labels)
        with video_path.open("rb") as handle:
            response = client.post("/analyze?objective=comprehensive_summary", files={"file": (video_path.name, handle, "image/gif")})
        assert response.status_code == 200

    setup = client.get("/setup/status").json()
    assert setup["bootstrap"] == {"count": 2, "threshold": 2, "locked": False}
    recommendations = client.get("/recommendations").json()
    assert recommendations == {
        "status": "unlocked",
        "bootstrap": {"count": 2, "threshold": 2, "locked": False},
        "message": "recommendations and production rankings are available",
        "items": [],
    }


def test_denied_failed_and_cancelled_executions_do_not_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    video_path = tmp_path / "sample.gif"
    _make_video(video_path, ["DENY"])

    class Denied:
        value = "deny"

    monkeypatch.setattr(app_module, "authorize", lambda *args, **kwargs: Denied())
    with video_path.open("rb") as handle:
        denied = client.post("/analyze?objective=comprehensive_summary", files={"file": ("sample.gif", handle, "image/gif")})
    assert denied.status_code == 403

    monkeypatch.setattr(app_module, "authorize", lambda *args, **kwargs: type("Allow", (), {"value": "allow"})())
    monkeypatch.setattr(app_module, "analyze_video_file", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("cancelled")))
    client = TestClient(app_module.app, raise_server_exceptions=False)
    with video_path.open("rb") as handle:
        failed = client.post("/analyze?objective=comprehensive_summary", files={"file": ("sample.gif", handle, "image/gif")})
    assert failed.status_code == 500

    assert client.get("/setup/status").json()["bootstrap"] == {"count": 0, "threshold": 2, "locked": True}


def test_tenant_isolation_keeps_bootstrap_counts_separate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, dependencies = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    video_path = tmp_path / "sample.gif"
    _make_video(video_path, ["TENANT"])

    def fake_analyze(**kwargs):
        return _qualified_result(
            tenant_id=kwargs["tenant_id"],
            source_id=kwargs["source_id"],
            source_revision_id=kwargs["source_revision_id"],
            source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
            objective_type=kwargs["objective_type"],
        )

    monkeypatch.setattr(app_module, "analyze_video_file", fake_analyze)
    with video_path.open("rb") as handle:
        response = client.post(
            "/analyze?objective=comprehensive_summary",
            files={"file": ("sample.gif", handle, "image/gif")},
            headers={"X-AgentView-Tenant": "tenant-a"},
        )
    assert response.status_code == 200
    default_tenant_id = dependencies.default_context().tenant_id
    assert dependencies.store.bootstrap_progress(default_tenant_id, 2) == {"count": 0, "threshold": 2, "locked": True}


def test_empty_upload_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)

    monkeypatch.setattr(app_module, "analyze_video_file", lambda **kwargs: _qualified_result(
        tenant_id=kwargs["tenant_id"],
        source_id=kwargs["source_id"],
        source_revision_id=kwargs["source_revision_id"],
        source_fingerprint_sha256=kwargs["source_fingerprint_sha256"],
        objective_type=kwargs["objective_type"],
    ))
    response = client.post(
        "/analyze?objective=comprehensive_summary",
        files={"file": ("empty.gif", b"", "image/gif")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "empty upload"


def test_oversized_upload_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ["AGENTVIEW_MAX_UPLOAD_BYTES"] = "1"
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    response = client.post(
        "/analyze?objective=comprehensive_summary",
        files={"file": ("big.gif", b"12", "image/gif")},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "upload too large"
    os.environ.pop("AGENTVIEW_MAX_UPLOAD_BYTES", None)


def test_unsupported_media_type_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module, _ = _reload_app(tmp_path)
    client = TestClient(app_module.app)
    response = client.post(
        "/analyze?objective=comprehensive_summary",
        files={"file": ("bad.txt", b"not media", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "unsupported media type"
