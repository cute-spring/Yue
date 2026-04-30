import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT_DIR / "data" / "skills" / "excalidraw-diagram-generator"
ADD_ICON_SCRIPT_PATH = SKILL_DIR / "scripts" / "add-icon-to-diagram.py"
ADD_ARROW_SCRIPT_PATH = SKILL_DIR / "scripts" / "add-arrow.py"


def _load_module(module_name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_add_arrow_script_main_happy_path_without_icon_library(tmp_path, monkeypatch):
    module = _load_module("add_arrow_module", ADD_ARROW_SCRIPT_PATH)
    diagram_path = tmp_path / "demo.excalidraw"
    _write_json(diagram_path, {"type": "excalidraw", "elements": []})

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "add-arrow.py",
            str(diagram_path),
            "10",
            "20",
            "110",
            "220",
            "--label",
            "HTTP",
        ],
    )
    module.main()

    updated = json.loads(diagram_path.read_text(encoding="utf-8"))
    assert len(updated["elements"]) == 2
    assert any(item["type"] == "arrow" for item in updated["elements"])


def test_add_icon_script_main_happy_path_with_icon_library(tmp_path, monkeypatch):
    module = _load_module("add_icon_module_happy", ADD_ICON_SCRIPT_PATH)
    diagram_path = tmp_path / "demo.excalidraw"
    _write_json(diagram_path, {"type": "excalidraw", "elements": []})

    library_dir = tmp_path / "aws-icons"
    icon_file = library_dir / "icons" / "EC2.json"
    _write_json(
        icon_file,
        {
            "name": "EC2",
            "elements": [
                {"id": "old-1", "type": "rectangle", "x": 1, "y": 2, "width": 40, "height": 20},
            ],
        },
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "add-icon-to-diagram.py",
            str(diagram_path),
            "EC2",
            "100",
            "200",
            "--library-path",
            str(library_dir),
            "--label",
            "web",
        ],
    )
    module.main()

    updated = json.loads(diagram_path.read_text(encoding="utf-8"))
    assert len(updated["elements"]) == 2
    assert any(item["type"] == "text" and item["text"] == "web" for item in updated["elements"])


def test_add_icon_script_main_fails_when_icon_not_found_and_restores_original_file(tmp_path, monkeypatch):
    module = _load_module("add_icon_module_missing_icon", ADD_ICON_SCRIPT_PATH)
    diagram_path = tmp_path / "demo.excalidraw"
    _write_json(diagram_path, {"type": "excalidraw", "elements": []})

    library_dir = tmp_path / "aws-icons"
    (library_dir / "icons").mkdir(parents=True, exist_ok=True)
    original_content = diagram_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "add-icon-to-diagram.py",
            str(diagram_path),
            "MISSING_ICON",
            "100",
            "200",
            "--library-path",
            str(library_dir),
        ],
    )

    with pytest.raises(SystemExit):
        module.main()

    assert diagram_path.exists()
    assert not diagram_path.with_suffix(".excalidraw.edit").exists()
    assert diagram_path.read_text(encoding="utf-8") == original_content


def test_add_icon_script_main_fails_when_edit_file_conflicts(tmp_path, monkeypatch):
    module = _load_module("add_icon_module_conflict", ADD_ICON_SCRIPT_PATH)
    diagram_path = tmp_path / "demo.excalidraw"
    _write_json(diagram_path, {"type": "excalidraw", "elements": []})
    diagram_path.with_suffix(".excalidraw.edit").write_text("{}", encoding="utf-8")

    library_dir = tmp_path / "aws-icons"
    (library_dir / "icons").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "add-icon-to-diagram.py",
            str(diagram_path),
            "EC2",
            "100",
            "200",
            "--library-path",
            str(library_dir),
        ],
    )
    with pytest.raises(SystemExit):
        module.main()


def test_add_icon_script_main_fails_on_invalid_diagram_json_and_restores_original_file(tmp_path, monkeypatch):
    module = _load_module("add_icon_module_invalid_json", ADD_ICON_SCRIPT_PATH)
    diagram_path = tmp_path / "demo.excalidraw"
    diagram_path.write_text("{invalid-json", encoding="utf-8")

    library_dir = tmp_path / "aws-icons"
    icon_file = library_dir / "icons" / "EC2.json"
    _write_json(
        icon_file,
        {
            "name": "EC2",
            "elements": [
                {"id": "old-1", "type": "rectangle", "x": 1, "y": 2, "width": 40, "height": 20},
            ],
        },
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "add-icon-to-diagram.py",
            str(diagram_path),
            "EC2",
            "100",
            "200",
            "--library-path",
            str(library_dir),
        ],
    )
    with pytest.raises(SystemExit):
        module.main()

    assert diagram_path.exists()
    assert not diagram_path.with_suffix(".excalidraw.edit").exists()
    assert diagram_path.read_text(encoding="utf-8") == "{invalid-json"
