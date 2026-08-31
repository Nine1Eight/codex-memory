from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-path", default=str(Path.home() / ".agentview.sqlite3"))
    parser.add_argument("--mode", choices=["sqlite", "postgres"], default="sqlite")
    parser.add_argument("--psql", default="psql")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    migration = root / "migrations" / "0001_initial.sql"

    if args.mode == "sqlite":
        if Path(args.database_path).exists():
            Path(args.database_path).unlink()
        conn = sqlite3.connect(args.database_path)
        try:
            conn.executescript(migration.read_text())
            conn.commit()
        finally:
            conn.close()
        return 0

    subprocess.run(
        [args.psql, "-v", "ON_ERROR_STOP=1", "-f", str(migration)],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
