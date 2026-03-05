import os
import sys
from pathlib import Path

from pptx import Presentation

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from generate_pptx import build_presentation, normalize_legacy_schema


def main() -> int:
    payload = {
        "title": "PPTX Smoke Test",
        "subtitle": "Backend verification",
        "slides": [
            {"type": "title", "title": "PPTX Smoke Test", "subtitle": "Backend verification"},
            {"type": "content", "title": "", "content": ["First point", {"text": "Dict bullet"}, 42, None]},
            {"type": "table", "title": "Table Fallback", "columns": [], "rows": [[1, 2], [3, 4]]},
            {"type": "chart", "title": "Chart Fallback", "chart": {"type": "bar", "categories": ["Q1", "Q2"]}},
            {"type": "quote", "quote": "", "author": "Anonymous"},
        ],
    }
    data = normalize_legacy_schema(payload)
    prs, _ = build_presentation(data)
    exports_dir = CURRENT_DIR.parents[3] / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    output_path = exports_dir / "pptx_smoke_test.pptx"
    prs.save(str(output_path))
    if not output_path.exists() or os.path.getsize(output_path) == 0:
        raise RuntimeError("PPTX output was not created")
    loaded = Presentation(str(output_path))
    if len(loaded.slides) == 0:
        raise RuntimeError("PPTX contains no slides")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
