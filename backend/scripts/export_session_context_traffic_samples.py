from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.services.memory.traffic_sample_export import export_traffic_derived_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Export redacted session-context traffic-derived candidate samples.")
    parser.add_argument(
        "--db-path",
        default=os.path.expanduser("~/.yue/data/yue.db"),
        help="Path to the Yue sqlite database. Defaults to ~/.yue/data/yue.db",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Write the redacted candidate export JSON to this path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of candidate sessions to export.",
    )
    args = parser.parse_args()

    export = export_traffic_derived_candidates(db_path=args.db_path, limit=max(1, args.limit))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "exported_at": export.exported_at,
                "source_db_path": export.source_db_path,
                "total_sessions_scanned": export.total_sessions_scanned,
                "eligible_sessions": export.eligible_sessions,
                "exported_candidates": export.exported_candidates,
                "fixtures": export.fixtures,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
