import pytest
import os
import tempfile
from app.services.skill_service import SkillLoader, SkillValidator, SkillSpec, SkillRegistry

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

if __name__ == "__main__":
    pytest.main([__file__])
