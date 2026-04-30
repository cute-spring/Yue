from pathlib import Path

from app.services.skill_service import SkillLoader


def _excalidraw_skill_dir() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "skills"
        / "excalidraw-diagram-generator"
    )


def test_excalidraw_skill_has_explicit_manifest_with_core_actions():
    package = SkillLoader.parse_package(_excalidraw_skill_dir())

    assert package.manifest_path is not None
    assert package.metadata.get("generated_manifest") is not True
    assert [script.id for script in package.scripts] == [
        "add-arrow.py",
        "add-icon-to-diagram.py",
        "split-excalidraw-library.py",
    ]
    assert [action.id for action in package.actions] == [
        "add_icon_to_diagram",
        "add_arrow_to_diagram",
        "split_excalidraw_library",
    ]


def test_excalidraw_skill_markdown_declares_capability_levels():
    skill_markdown = (_excalidraw_skill_dir() / "SKILL.md").read_text(encoding="utf-8")

    assert "## Capability Levels" in skill_markdown
    assert "- L1: Basic diagram generation (no icon library required)" in skill_markdown
    assert "- L2: Professional icon diagram generation (icon library required)" in skill_markdown
    assert "- L3: Auto enhancement (icon + arrows + labels)" in skill_markdown
