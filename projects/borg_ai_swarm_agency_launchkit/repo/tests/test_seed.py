from pathlib import Path
from borg_seed.capsule import create_borg_archive, inspect_borg_archive


def test_create_and_inspect_seed(tmp_path: Path):
    out = tmp_path / "seed.borg"
    create_borg_archive(out)
    info = inspect_borg_archive(out)
    assert info["sha256"]
    assert info["manifest"]["schema_version"] == "borg.seed.v1"
    assert info["manifest"]["safety_contract"] == "authorized-forking-signed-sync-no-auto-exec"
