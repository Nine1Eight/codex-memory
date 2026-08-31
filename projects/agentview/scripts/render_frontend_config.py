from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """window.AGENTVIEW_API_BASE_URL = "{api_base_url}";
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--api-base-url", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.write_text(TEMPLATE.format(api_base_url=args.api_base_url), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
