from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
import tempfile
import uuid

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
for path in (APP_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fastapi import FastAPI, Header, HTTPException
from fastapi import File, Form, UploadFile
from fastapi.responses import JSONResponse

from packages.identity import authorize
from packages.persistence import Role

from packages.analysis import analyze_video_file

from .config import load_config
from .dependencies import RequestContext, default_context, policy_for, store
from .receipt import make_receipt, receipt_to_json

app = FastAPI(title="AgentView API", version="0.1.0")


def _context_from_headers(x_agentview_tenant: str | None, x_agentview_principal: str | None) -> RequestContext:
    bootstrap = default_context()
    tenant_id = x_agentview_tenant or bootstrap.tenant_id
    principal_id = x_agentview_principal or bootstrap.principal_id
    return RequestContext(tenant_id=tenant_id, principal_id=principal_id, role=Role.ADMIN)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, bool]:
    return {"ready": True}


def _setup_status(tenant_id: str | None = None) -> dict[str, object]:
    config = load_config()
    bootstrap = default_context()
    resolved_tenant_id = tenant_id or bootstrap.tenant_id
    progress = store.bootstrap_progress(resolved_tenant_id, config.bootstrap_threshold)
    return {**config.__dict__, "bootstrap": progress}


def _validate_upload(file: UploadFile, upload_bytes: bytes) -> None:
    if not upload_bytes:
        raise HTTPException(status_code=400, detail="empty upload")
    config = load_config()
    if len(upload_bytes) > config.max_upload_bytes:
        raise HTTPException(status_code=413, detail="upload too large")
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in {
        "image/gif",
        "image/webp",
        "image/png",
        "image/jpeg",
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=415, detail="unsupported media type")


@app.get("/setup/status")
def setup_status(
    x_agentview_tenant: str | None = Header(default=None, alias="X-AgentView-Tenant"),
) -> dict[str, object]:
    return _setup_status(x_agentview_tenant)


@app.post("/sources")
def create_source(
    payload: dict[str, str],
    x_agentview_tenant: str | None = Header(default=None, alias="X-AgentView-Tenant"),
    x_agentview_principal: str | None = Header(default=None, alias="X-AgentView-Principal"),
) -> dict[str, str]:
    ctx = _context_from_headers(x_agentview_tenant, x_agentview_principal)
    if authorize(policy_for(ctx), "source.create").value != "allow":
        raise HTTPException(status_code=403, detail="not allowed")
    source = store.create_source(ctx.tenant_id, payload["title"], payload["sourceType"], ctx.principal_id)
    return {"id": source.id, "tenantId": source.tenant_id, "title": source.title}


@app.post("/sources/{source_id}/authority-grants")
def create_authority_grant(
    source_id: str,
    payload: dict[str, str],
    x_agentview_tenant: str | None = Header(default=None, alias="X-AgentView-Tenant"),
    x_agentview_principal: str | None = Header(default=None, alias="X-AgentView-Principal"),
) -> dict[str, str]:
    ctx = _context_from_headers(x_agentview_tenant, x_agentview_principal)
    if authorize(policy_for(ctx), "authority.grant.create").value != "allow":
        raise HTTPException(status_code=403, detail="not allowed")
    grant = store.create_authority_grant(
        ctx.tenant_id,
        source_id,
        payload["authorityClass"],
        datetime.now(timezone.utc),
        None,
        ctx.principal_id,
    )
    return {"id": grant.id, "sourceId": grant.source_id, "status": grant.status}


@app.get("/audit-events")
def audit_events(
    x_agentview_tenant: str | None = Header(default=None, alias="X-AgentView-Tenant"),
) -> dict[str, list[dict[str, str]]]:
    bootstrap = default_context()
    tenant_id = x_agentview_tenant or bootstrap.tenant_id
    events = store.audit_events(tenant_id)
    return {
        "items": [
            {"id": e.id, "resource_id": e.resource_id, "action": e.action, "decision": e.decision}
            for e in events
        ]
    }


@app.get("/recommendations")
def recommendations(
    x_agentview_tenant: str | None = Header(default=None, alias="X-AgentView-Tenant"),
) -> dict[str, object]:
    bootstrap = default_context()
    tenant_id = x_agentview_tenant or bootstrap.tenant_id
    config = load_config()
    progress = store.bootstrap_progress(tenant_id, config.bootstrap_threshold)
    if progress["locked"]:
        return {
            "status": "locked",
            "bootstrap": progress,
            "message": f"bootstrap mode requires {config.bootstrap_threshold} qualified multimodal views before rankings unlock",
        }
    return {
        "status": "unlocked",
        "bootstrap": progress,
        "message": "recommendations and production rankings are available",
        "items": [],
    }


@app.post("/analyze")
def analyze(
    objective: str,
    transcript: str = Form(default=""),
    file: UploadFile = File(...),
    x_agentview_tenant: str | None = Header(default=None, alias="X-AgentView-Tenant"),
    x_agentview_principal: str | None = Header(default=None, alias="X-AgentView-Principal"),
) -> JSONResponse:
    ctx = _context_from_headers(x_agentview_tenant, x_agentview_principal)
    if authorize(policy_for(ctx), "source.create").value != "allow":
        raise HTTPException(status_code=403, detail="not allowed")
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / Path(file.filename).name
        upload_bytes = file.file.read()
        _validate_upload(file, upload_bytes)
        video_path.write_bytes(upload_bytes)
        source_fingerprint = hashlib.sha256(upload_bytes).hexdigest()
        source = store.create_source(ctx.tenant_id, file.filename, "uploaded_media", ctx.principal_id)
        revision = store.create_revision(ctx.tenant_id, source.id, f"sha256:{source_fingerprint}", {"objective": objective}, None, ctx.principal_id)
        store.create_authority_grant(ctx.tenant_id, source.id, "owned_media", datetime.now(timezone.utc), None, ctx.principal_id)
        analysis = analyze_video_file(
            tenant_id=ctx.tenant_id,
            agent_id="agent-1",
            agent_version_id="agent-version-1",
            source_id=source.id,
            source_revision_id=revision.id,
            source_fingerprint_sha256=f"sha256:{source_fingerprint}",
            source_type=source.source_type,
            authority_class="owned_media",
            objective_id="objective-1",
            objective_type=objective,
            job_id=str(uuid.uuid4()),
            video_path=video_path,
            transcript=transcript,
        )
        receipt = make_receipt(str(uuid.uuid4()), analysis.receipt_payload, analysis.receipt_signature)
        if analysis.receipt_payload.qualified and analysis.receipt_payload.view_class.value == "multimodal":
            store.record_bootstrap_view(
                tenant_id=ctx.tenant_id,
                source_fingerprint_sha256=analysis.receipt_payload.source_fingerprint_sha256,
                source_id=source.id,
                source_revision_id=revision.id,
                receipt_id=receipt.receipt_id,
                objective_type=objective,
                view_class=analysis.receipt_payload.view_class.value,
                qualified=analysis.receipt_payload.qualified,
                actor=ctx.principal_id,
            )
        return JSONResponse(
            {
                "summary": analysis.summary,
                "transcriptExcerpt": analysis.transcript_excerpt,
                "frameTexts": list(analysis.frame_texts),
                "claims": [claim.__dict__ for claim in analysis.claims],
                "receipt": receipt_to_json(receipt),
                "bootstrap": store.bootstrap_progress(ctx.tenant_id, load_config().bootstrap_threshold),
            }
        )
