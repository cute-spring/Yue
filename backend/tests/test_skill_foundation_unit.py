import pytest
import os
import tempfile
import platform
from app.services.skill_service import SkillLoader, SkillValidator, SkillSpec, SkillRegistry, SkillRouter

def test_skill_loader_parse_markdown():
    content = """---
name: code-architect
version: 1.0.0
description: A skill for code architecture
capabilities: ["design", "uml"]
entrypoint: system_prompt
---
## System Prompt
You are a code architect.

## Instructions
Design systems with UML.

## Examples
User: How to design a login system?
Assistant: Use OAuth2.
"""
    spec = SkillLoader.parse_markdown(content, source_path="test.md")
    assert spec is not None
    assert spec.name == "code-architect"
    assert spec.version == "1.0.0"
    assert spec.system_prompt == "You are a code architect."
    assert spec.instructions == "Design systems with UML."
    assert "Design systems with UML." in spec.instructions
    assert "User: How to design a login system?" in spec.examples

def test_skill_loader_parse_always_flag():
    content = """---
name: always-skill
version: 1.0.0
description: always
capabilities: ["always"]
entrypoint: system_prompt
always: true
---
## System Prompt
Always.
"""
    spec = SkillLoader.parse_markdown(content, source_path="always.md")
    assert spec is not None
    assert spec.always is True

def test_skill_validator_valid():
    spec = SkillSpec(
        name="test-skill",
        version="1.1.0",
        description="test",
        capabilities=["test"],
        entrypoint="system_prompt",
        system_prompt="You are a test skill."
    )
    result = SkillValidator.validate(spec)
    assert result.is_valid is True
    assert len(result.errors) == 0

def test_skill_validator_invalid_missing_name():
    spec = SkillSpec(
        name="",
        version="1.1.0",
        description="test",
        capabilities=["test"],
        entrypoint="system_prompt",
        system_prompt="You are a test skill."
    )
    result = SkillValidator.validate(spec)
    assert result.is_valid is False
    assert "Skill name is required" in result.errors

def test_skill_validator_invalid_missing_entrypoint_section():
    spec = SkillSpec(
        name="test-skill",
        version="1.1.0",
        description="test",
        capabilities=["test"],
        entrypoint="missing_section",
        system_prompt="You are a test skill."
    )
    result = SkillValidator.validate(spec)
    assert result.is_valid is False
    assert "Entrypoint section 'missing_section' not found in Markdown" in result.errors

def test_skill_registry_load_and_get():
    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_content = """---
name: test-skill
version: 1.0.0
description: test
capabilities: ["test"]
entrypoint: system_prompt
---
## System Prompt
Test prompt.
"""
        skill_path = os.path.join(tmp_dir, "test.md")
        with open(skill_path, "w") as f:
            f.write(skill_content)
        
        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()
        
        skill = registry.get_skill("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"
        assert skill.version == "1.0.0"
        
        # Test versioning
        skill_content_v2 = """---
name: test-skill
version: 2.0.0
description: test v2
capabilities: ["test"]
entrypoint: system_prompt
---
## System Prompt
Test prompt v2.
"""
        skill_path_v2 = os.path.join(tmp_dir, "test_v2.md")
        with open(skill_path_v2, "w") as f:
            f.write(skill_content_v2)
        
        registry.load_all()
        assert len(registry.list_skills()) == 2
        
        latest = registry.get_skill("test-skill")
        assert latest.version == "2.0.0"
        
        v1 = registry.get_skill("test-skill", version="1.0.0")
        assert v1.version == "1.0.0"

def test_skill_registry_package_loading():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "pkg-skill")
        os.makedirs(pkg_dir, exist_ok=True)
        pkg_content = """---
name: package-skill
version: 1.0.0
description: packaged
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Package prompt.
"""
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write(pkg_content)
        with open(os.path.join(pkg_dir, "notes.md"), "w") as f:
            f.write("not a skill")

        legacy_content = """---
name: legacy-skill
version: 1.0.0
description: legacy
capabilities: ["legacy"]
entrypoint: system_prompt
---
## System Prompt
Legacy prompt.
"""
        with open(os.path.join(tmp_dir, "legacy.md"), "w") as f:
            f.write(legacy_content)

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()
        names = sorted([s.name for s in registry.list_skills()])
        assert names == ["legacy-skill", "package-skill"]

def test_skill_registry_directory_priority_user_over_workspace_over_builtin():
    with tempfile.TemporaryDirectory() as root_dir:
        builtin_dir = os.path.join(root_dir, "builtin")
        workspace_dir = os.path.join(root_dir, "workspace")
        user_dir = os.path.join(root_dir, "user")
        os.makedirs(builtin_dir, exist_ok=True)
        os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(user_dir, exist_ok=True)

        skill_name = "layered-skill"
        version = "1.0.0"
        template = """---
name: {name}
version: {version}
description: {description}
capabilities: ["layered"]
entrypoint: system_prompt
---
## System Prompt
{prompt}
"""
        with open(os.path.join(builtin_dir, "layered.md"), "w") as f:
            f.write(template.format(name=skill_name, version=version, description="builtin", prompt="BUILTIN"))
        with open(os.path.join(workspace_dir, "layered.md"), "w") as f:
            f.write(template.format(name=skill_name, version=version, description="workspace", prompt="WORKSPACE"))
        with open(os.path.join(user_dir, "layered.md"), "w") as f:
            f.write(template.format(name=skill_name, version=version, description="user", prompt="USER"))

        registry = SkillRegistry(skill_dirs=[user_dir, builtin_dir, workspace_dir])
        registry.load_all()
        selected = registry.get_skill(skill_name, version)
        assert selected is not None
        assert selected.system_prompt == "USER"

def test_skill_registry_get_full_skill_from_source_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "lazy-skill")
        os.makedirs(pkg_dir, exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: lazy-skill
version: 1.0.0
description: lazy
capabilities: ["lazy"]
entrypoint: system_prompt
---
## System Prompt
Lazy prompt.
""")
        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()
        full = registry.get_full_skill("lazy-skill", "1.0.0")
        assert full is not None
        assert full.system_prompt == "Lazy prompt."

def test_skill_registry_availability_missing_requirements():
    os.environ.pop("SKILL_TEST_MISSING_ENV", None)
    registry = SkillRegistry()
    spec = SkillSpec(
        name="requires-skill",
        version="1.0.0",
        description="reqs",
        capabilities=["reqs"],
        entrypoint="system_prompt",
        system_prompt="test",
        requires={"bins": ["__missing_bin__"], "env": ["SKILL_TEST_MISSING_ENV"]},
        os=[platform.system().lower()]
    )
    registry.register(spec)
    loaded = registry.get_skill("requires-skill")
    assert loaded is not None
    assert loaded.availability is False
    assert "bins" in (loaded.missing_requirements or {})
    assert "env" in (loaded.missing_requirements or {})

def test_skill_router_filters_unavailable():
    os.environ.pop("SKILL_TEST_MISSING_ENV", None)
    registry = SkillRegistry()
    available_skill = SkillSpec(
        name="available-skill",
        version="1.0.0",
        description="ok",
        capabilities=["ok"],
        entrypoint="system_prompt",
        system_prompt="ok",
        os=[platform.system().lower()]
    )
    unavailable_skill = SkillSpec(
        name="blocked-skill",
        version="1.0.0",
        description="blocked",
        capabilities=["blocked"],
        entrypoint="system_prompt",
        system_prompt="blocked",
        requires={"bins": ["__missing_bin__"], "env": ["SKILL_TEST_MISSING_ENV"]},
        os=[platform.system().lower()]
    )
    registry.register(available_skill)
    registry.register(unavailable_skill)
    router = SkillRouter(registry)
    agent = type("Agent", (), {"visible_skills": ["available-skill", "blocked-skill"]})()
    selected, _score = router.route_with_score(agent, "available")
    assert selected is not None
    assert selected.name == "available-skill"
    selected, _score = router.route_with_score(agent, "blocked", requested_skill="blocked-skill")
    assert selected is None

def test_skill_router_infer_requested_skill_from_message():
    registry = SkillRegistry()
    planner = SkillSpec(
        name="release-test-planner",
        version="1.2.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        system_prompt="planner",
        os=[platform.system().lower()]
    )
    debugger = SkillSpec(
        name="backend-api-debugger",
        version="1.0.0",
        description="debug",
        capabilities=["debug"],
        entrypoint="system_prompt",
        system_prompt="debugger",
        os=[platform.system().lower()]
    )
    registry.register(planner)
    registry.register(debugger)
    router = SkillRouter(registry)
    agent = type("Agent", (), {"visible_skills": ["release-test-planner", "backend-api-debugger"]})()

    inferred = router.infer_requested_skill(agent, "请使用 backend-api-debugger 来排查这个 500 错误")
    assert inferred == "backend-api-debugger:1.0.0"

    selected, score = router.route_with_score(agent, "请使用 backend-api-debugger 来排查这个 500 错误")
    assert selected is not None
    assert selected.name == "backend-api-debugger"
    assert score == 1000

def test_skill_router_requested_skill_still_has_highest_priority():
    registry = SkillRegistry()
    planner = SkillSpec(
        name="release-test-planner",
        version="1.2.0",
        description="planner",
        capabilities=["planning"],
        entrypoint="system_prompt",
        system_prompt="planner",
        os=[platform.system().lower()]
    )
    debugger = SkillSpec(
        name="backend-api-debugger",
        version="1.0.0",
        description="debug",
        capabilities=["debug"],
        entrypoint="system_prompt",
        system_prompt="debugger",
        os=[platform.system().lower()]
    )
    registry.register(planner)
    registry.register(debugger)
    router = SkillRouter(registry)
    agent = type("Agent", (), {"visible_skills": ["release-test-planner", "backend-api-debugger"]})()

    selected, score = router.route_with_score(
        agent,
        "这里更像 planning 任务，但请用 backend-api-debugger",
        requested_skill="release-test-planner:1.2.0"
    )
    assert selected is not None
    assert selected.name == "release-test-planner"
    assert score == 1000

def test_skill_router_offline_replay_hit_rate():
    registry = SkillRegistry()
    planner = SkillSpec(
        name="release-test-planner",
        version="1.0.0",
        description="Generate release plan and milestones",
        capabilities=["planning", "release-management"],
        entrypoint="system_prompt",
        system_prompt="planner",
        os=[platform.system().lower()]
    )
    pdf_skill = SkillSpec(
        name="pdf-insight-extractor",
        version="1.0.0",
        description="Extract key points and evidence from PDF",
        capabilities=["pdf-analysis", "summarization"],
        entrypoint="system_prompt",
        system_prompt="pdf",
        os=[platform.system().lower()]
    )
    excel_skill = SkillSpec(
        name="excel-metric-explorer",
        version="1.0.0",
        description="Analyze excel metrics and grouped statistics",
        capabilities=["excel", "data-analysis"],
        entrypoint="system_prompt",
        system_prompt="excel",
        os=[platform.system().lower()]
    )
    registry.register(planner)
    registry.register(pdf_skill)
    registry.register(excel_skill)
    router = SkillRouter(registry)
    agent = type("Agent", (), {"visible_skills": [
        "release-test-planner:1.0.0",
        "pdf-insight-extractor:1.0.0",
        "excel-metric-explorer:1.0.0",
    ]})()

    replay_cases = [
        ("please create a release planning milestones checklist", "release-test-planner"),
        ("extract key evidence from this pdf and summarize", "pdf-insight-extractor"),
        ("analyze this excel sales sheet and rank top regions", "excel-metric-explorer"),
        ("build a release-management plan with rollout phases", "release-test-planner"),
        ("pdf-analysis task: summarize risk sections with evidence", "pdf-insight-extractor"),
        ("excel data-analysis for anomalies and grouped totals", "excel-metric-explorer"),
        ("写一段问候语", None),
    ]
    hit = 0
    valid = 0
    for task, expected in replay_cases:
        selected, _score = router.route_with_score(agent, task)
        if expected is None:
            continue
        valid += 1
        if selected and selected.name == expected:
            hit += 1
    hit_rate = hit / valid
    assert hit_rate >= 0.8

if __name__ == "__main__":
    pytest.main([__file__])
