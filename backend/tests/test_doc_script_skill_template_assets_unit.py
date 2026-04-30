from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "backend" / "data" / "skills" / "_templates" / "doc-script-skill"
MANIFEST_EXAMPLE = TEMPLATE_DIR / "manifest.yaml.example"
SKILL_MD_EXAMPLE = TEMPLATE_DIR / "SKILL.md.example"
GUIDE_DOC = (
    REPO_ROOT
    / "docs"
    / "guides"
    / "developer"
    / "DOC_SCRIPT_SKILL_TEMPLATE_GUIDE.md"
)
ROLLOUT_PLAN = REPO_ROOT / "docs" / "superpowers" / "plans" / "skill-template-rollout-targets.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_doc_script_template_files_exist() -> None:
    assert TEMPLATE_DIR.exists()
    assert MANIFEST_EXAMPLE.exists()
    assert SKILL_MD_EXAMPLE.exists()
    assert GUIDE_DOC.exists()
    assert ROLLOUT_PLAN.exists()


def test_manifest_example_contains_required_structure() -> None:
    content = _read_text(MANIFEST_EXAMPLE)
    assert "name:" in content
    assert "version:" in content
    assert "entrypoint:" in content
    assert "actions:" in content
    assert "input_schema:" in content
    assert "output_schema:" in content


def test_skill_markdown_example_contains_required_sections() -> None:
    content = _read_text(SKILL_MD_EXAMPLE)
    assert "# " in content
    assert "## Capability Levels" in content
    assert "## Actions" in content
    assert "## Directory Layout" in content
    assert "## Migration: Read-only to Action Skill" in content


def test_guide_contains_template_conventions_and_migration_steps() -> None:
    content = _read_text(GUIDE_DOC)
    assert "references/" in content
    assert "scripts/" in content
    assert "templates/" in content
    assert "libraries/" in content
    assert "actions" in content
    assert "Required Fields" in content
    assert "Migration Steps" in content


def test_rollout_plan_contains_targets_priority_and_owners() -> None:
    content = _read_text(ROLLOUT_PLAN)
    assert "# Skill Template Rollout Targets" in content
    assert "Target Skill" in content
    assert "Priority" in content
    assert "Owner" in content
    assert "Acceptance Criteria" in content
