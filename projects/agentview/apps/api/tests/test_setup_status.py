from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys


def _reload_main(tmp_path: Path):
    os.environ["AGENTVIEW_DATABASE_PATH"] = str(tmp_path / "setup.sqlite3")
    os.environ["AGENTVIEW_BOOTSTRAP_THRESHOLD"] = "2"
    for module in [
        "agentview_api.main",
        "agentview_api.app",
        "agentview_api.dependencies",
    ]:
        sys.modules.pop(module, None)
    import agentview_api.main as main_module
    importlib.reload(main_module)
    return main_module


def test_setup_status_reports_exact_bootstrap_state(tmp_path: Path) -> None:
    app = _reload_main(tmp_path)
    import agentview_api.app as app_module

    status = app_module._setup_status()

    assert status["bootstrap"] == {"count": 0, "threshold": 2, "locked": True}
    assert status["bootstrap_threshold"] == 2
    assert status["database_mode"] == "sqlite"


def test_setup_status_uses_tenant_header(tmp_path: Path) -> None:
    app = _reload_main(tmp_path)
    from fastapi.testclient import TestClient

    client = TestClient(app.app)
    response = client.get("/setup/status", headers={"X-AgentView-Tenant": "tenant-x"})

    assert response.status_code == 200
    assert response.json()["bootstrap"] == {"count": 0, "threshold": 2, "locked": True}


def test_live_and_ready_helpers() -> None:
    from agentview_api import main as app

    assert app.live()["status"] == "ok"
    assert app.ready()["ready"] is True
