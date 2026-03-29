import pytest
import os
import tempfile
import platform
from types import SimpleNamespace
from app.services.skill_service import (
    DefaultBrowserContinuityLookupBackend,
    MarkdownSkillAdapter,
    DefaultBrowserContinuityResolver,
    ExplicitContextBrowserContinuityResolver,
    RuntimeBrowserContinuityLookupRequest,
    RuntimeBrowserContinuityLookupResult,
    RuntimeBrowserContinuityResolutionRequest,
    RuntimeBrowserContinuityResolutionResult,
    RuntimeSkillActionApprovalRequest,
    RuntimeSkillActionDescriptor,
    RuntimeSkillActionExecutionRequest,
    RuntimeSkillActionInvocationRequest,
    RuntimeSkillActionInvocationResult,
    SkillActionExecutionService,
    build_action_approval_message,
    build_action_execution_transition_event,
    build_action_execution_stub_message,
    SkillConstraints,
    SkillLoader,
    SkillPolicyGate,
    SkillPackageSpec,
    SkillRegistry,
    SkillRouter,
    SkillSpec,
    SkillValidator,
    YueActionStateBrowserContinuityLookupBackend,
    build_action_execution_result_event,
    build_action_invocation_event,
)

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
        package_skill = registry.get_skill("package-skill")
        assert package_skill is not None
        assert package_skill.package_format == "package_directory"

def test_skill_loader_generates_minimal_manifest_for_package_without_manifest():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "pkg-skill")
        os.makedirs(os.path.join(pkg_dir, "references"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: package-skill
version: 1.0.0
description: packaged
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Package prompt.
""")
        with open(os.path.join(pkg_dir, "references", "guide.md"), "w") as f:
            f.write("# Guide")
        with open(os.path.join(pkg_dir, "scripts", "run.py"), "w") as f:
            f.write("print('hi')")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("interface:\n  display_name: Package Skill\n")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        assert package.manifest_path is None
        assert package.metadata.get("generated_manifest") is True
        assert [ref.path for ref in package.references] == ["references/guide.md"]
        assert [script.path for script in package.scripts] == ["scripts/run.py"]
        assert [overlay.path for overlay in package.overlays] == ["agents/openai.yaml"]
        assert package.overlays[0].provider == "openai"

def test_skill_loader_discovers_model_specific_overlay_from_filename():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "pkg-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: package-skill
version: 1.0.0
description: packaged
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Package prompt.
""")
        with open(os.path.join(pkg_dir, "agents", "openai.gpt-4o.yaml"), "w") as f:
            f.write("system_prompt: gpt-4o overlay\n")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        assert len(package.overlays) == 1
        assert package.overlays[0].provider == "openai"
        assert package.overlays[0].model == "gpt-4o"

def test_skill_loader_parse_package_manifest_and_normalize_to_skill_spec():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "manifested-skill")
        os.makedirs(os.path.join(pkg_dir, "references"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: package-skill
version: 1.0.0
description: markdown description
capabilities: ["pkg"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:exec"]
---
## System Prompt
Package prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: package-skill
version: 1.1.0
description: manifest description
entrypoint: system_prompt
capabilities:
  - pkg
  - manifest
loading:
  summary_fields:
    - name
    - description
  default_tier: prompt
resources:
  references:
    - path: references/guide.md
      kind: markdown
      load_tier: reference
  scripts:
    - id: generate
      path: scripts/run.py
      runtime: python
      load_tier: action
      safety: workspace_write
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
actions:
  - id: generate
    tool: builtin:docs_read
    resource: scripts/run.py
    runtime: python
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "references", "guide.md"), "w") as f:
            f.write("# Guide")
        with open(os.path.join(pkg_dir, "scripts", "run.py"), "w") as f:
            f.write("print('hi')")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("interface:\n  display_name: Package Skill\n")

        package = SkillLoader.parse_package(pkg_dir)
        assert isinstance(package, SkillPackageSpec)
        assert package.version == "1.1.0"
        assert package.description == "manifest description"
        assert package.loading.default_tier == "prompt"
        assert [ref.path for ref in package.references] == ["references/guide.md"]
        assert [script.runtime for script in package.scripts] == ["python"]
        assert [overlay.provider for overlay in package.overlays] == ["openai"]
        assert [action.id for action in package.actions] == ["generate"]

        normalized = SkillLoader.package_to_skill_spec(package)
        assert normalized.name == "package-skill"
        assert normalized.version == "1.1.0"
        assert normalized.system_prompt == "Package prompt."
        assert normalized.constraints is not None
        assert normalized.constraints.allowed_tools == ["builtin:exec"]
        assert normalized.package_format == "package_directory"
        assert normalized.manifest_path is not None
        assert normalized.metadata["package"]["action_count"] == 1

def test_skill_registry_exposes_package_manifest_and_full_skill_compatibility():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "manifested-skill")
        os.makedirs(os.path.join(pkg_dir, "references"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: package-skill
version: 1.0.0
description: markdown description
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Package prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: package-skill
version: 1.0.0
description: manifest description
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  references:
    - path: references/guide.md
      kind: markdown
""")
        with open(os.path.join(pkg_dir, "references", "guide.md"), "w") as f:
            f.write("# Guide")
        with open(os.path.join(pkg_dir, "scripts", "run.py"), "w") as f:
            f.write("print('hi')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        manifest = registry.get_package_manifest("package-skill")
        assert manifest is not None
        assert manifest.description == "manifest description"
        assert [ref.path for ref in manifest.references] == ["references/guide.md"]

        full = registry.get_full_skill("package-skill")
        assert full is not None
        assert full.description == "manifest description"
        assert full.system_prompt == "Package prompt."
        assert full.package_format == "package_directory"

def test_skill_loader_validate_package_reports_missing_declared_manifest_paths():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "broken-skill")
        os.makedirs(pkg_dir, exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: broken-skill
version: 1.0.0
description: broken
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Broken prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: broken-skill
version: 1.0.0
description: broken
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  references:
    - path: references/missing.md
      kind: markdown
  scripts:
    - id: run
      path: scripts/missing.py
      runtime: python
overlays:
  providers:
    - provider: openai
      path: agents/missing.yaml
actions:
  - id: run
    resource: scripts/missing.py
    runtime: python
""")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        validation = SkillLoader.validate_package(package)
        assert validation.is_valid is False
        assert "Declared reference path does not exist: references/missing.md" in validation.errors
        assert "Declared script path does not exist: scripts/missing.py" in validation.errors
        assert "Declared overlay path does not exist: agents/missing.yaml" in validation.errors
        assert "Declared action path does not exist: scripts/missing.py" in validation.errors

def test_skill_registry_skips_invalid_manifest_package_registration():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "broken-skill")
        os.makedirs(pkg_dir, exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: broken-skill
version: 1.0.0
description: broken
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Broken prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: broken-skill
version: 1.0.0
description: broken
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  references:
    - path: references/missing.md
      kind: markdown
""")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        assert registry.get_skill("broken-skill") is None
        assert registry.get_package_manifest("broken-skill") is None

def test_skill_registry_keeps_manifest_validation_warnings_for_undeclared_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "warn-skill")
        os.makedirs(os.path.join(pkg_dir, "references"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: warn-skill
version: 1.0.0
description: warning package
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Warn prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: warn-skill
version: 1.0.0
description: warning package
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  references: []
  scripts: []
""")
        with open(os.path.join(pkg_dir, "references", "extra.md"), "w") as f:
            f.write("# Extra")
        with open(os.path.join(pkg_dir, "scripts", "extra.py"), "w") as f:
            f.write("print('extra')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        skill = registry.get_skill("warn-skill")
        assert skill is not None
        warnings = (skill.metadata or {}).get("package_validation_warnings", [])
        assert any("Undeclared reference files discovered" in warning for warning in warnings)
        assert any("Undeclared script files discovered" in warning for warning in warnings)

def test_skill_loader_resolves_provider_overlay_into_runtime_skill_view():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "overlay-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: overlay-skill
version: 1.0.0
description: base description
capabilities: ["base"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:docs_read"]
---
## System Prompt
BASE PROMPT

## Instructions
BASE INSTRUCTIONS
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: overlay-skill
version: 1.0.0
description: base description
entrypoint: system_prompt
capabilities: ["base"]
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
""")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("""system_prompt: OPENAI PROMPT
instructions: OPENAI INSTRUCTIONS
capabilities: ["base", "openai"]
constraints:
  allowed_tools: ["builtin:exec"]
metadata:
  overlay_mode: openai
interface:
  display_name: Overlay Skill
""")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        base = registry.get_full_skill("overlay-skill")
        assert base is not None
        assert base.system_prompt == "BASE PROMPT"
        assert base.constraints is not None
        assert base.constraints.allowed_tools == ["builtin:docs_read"]

        resolved = registry.get_full_skill("overlay-skill", provider="openai", model_name="gpt-4o")
        assert resolved is not None
        assert resolved.system_prompt == "OPENAI PROMPT"
        assert resolved.instructions == "OPENAI INSTRUCTIONS"
        assert resolved.capabilities == ["base", "openai"]
        assert resolved.constraints is not None
        assert resolved.constraints.allowed_tools == ["builtin:exec"]
        assert resolved.metadata["overlay_mode"] == "openai"
        assert resolved.metadata["resolved_overlay"]["provider"] == "openai"

def test_skill_loader_resolves_model_specific_overlay_after_provider_overlay():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "overlay-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: overlay-skill
version: 1.0.0
description: base description
capabilities: ["base"]
entrypoint: system_prompt
constraints:
  allowed_tools: ["builtin:docs_read"]
---
## System Prompt
BASE PROMPT

## Instructions
BASE INSTRUCTIONS
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: overlay-skill
version: 1.0.0
description: base description
entrypoint: system_prompt
capabilities: ["base"]
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
    - provider: openai
      model: gpt-4o
      path: agents/openai.gpt-4o.yaml
""")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("""system_prompt: OPENAI PROMPT
metadata:
  overlay_level: provider
constraints:
  allowed_tools: ["builtin:exec"]
""")
        with open(os.path.join(pkg_dir, "agents", "openai.gpt-4o.yaml"), "w") as f:
            f.write("""instructions: GPT4O INSTRUCTIONS
metadata:
  overlay_level: model
""")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        resolved = registry.get_full_skill("overlay-skill", provider="openai", model_name="gpt-4o")
        assert resolved is not None
        assert resolved.system_prompt == "OPENAI PROMPT"
        assert resolved.instructions == "GPT4O INSTRUCTIONS"
        assert resolved.constraints is not None
        assert resolved.constraints.allowed_tools == ["builtin:exec"]
        assert resolved.metadata["overlay_level"] == "model"
        assert len(resolved.metadata["resolved_overlays"]) == 2
        assert resolved.metadata["resolved_overlays"][0]["path"] == "agents/openai.yaml"
        assert resolved.metadata["resolved_overlays"][1]["path"] == "agents/openai.gpt-4o.yaml"

def test_skill_loader_normalizes_action_resource_path_to_script_id():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - path: scripts/run.py
actions:
  - id: run
    resource: scripts/run.py
""")
        with open(os.path.join(pkg_dir, "scripts", "run.py"), "w") as f:
            f.write("print('run')")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        assert len(package.scripts) == 1
        assert package.scripts[0].id == "scripts-run.py"
        assert len(package.actions) == 1
        assert package.actions[0].resource == "scripts-run.py"
        assert package.actions[0].path == "scripts/run.py"
        assert package.actions[0].runtime == "python"

def test_skill_loader_validate_package_rejects_duplicate_overlay_and_action_ids():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "dup-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: dup-skill
version: 1.0.0
description: dup
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Dup prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: dup-skill
version: 1.0.0
description: dup
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: run
      path: scripts/run.py
      runtime: python
    - id: run
      path: scripts/run_alt.py
      runtime: python
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
    - provider: openai
      path: agents/openai_alt.yaml
actions:
  - id: run
    resource: run
  - id: run
    resource: run
""")
        with open(os.path.join(pkg_dir, "scripts", "run.py"), "w") as f:
            f.write("print('run')")
        with open(os.path.join(pkg_dir, "scripts", "run_alt.py"), "w") as f:
            f.write("print('run alt')")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("system_prompt: hi\n")
        with open(os.path.join(pkg_dir, "agents", "openai_alt.yaml"), "w") as f:
            f.write("system_prompt: hi alt\n")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        validation = SkillLoader.validate_package(package)
        assert validation.is_valid is False
        assert "Duplicate script ids declared in manifest" in validation.errors
        assert "Duplicate action ids declared in manifest" in validation.errors
        assert "Duplicate overlay providers declared in manifest" in validation.errors

def test_skill_loader_validate_package_allows_same_provider_for_different_models():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "multi-overlay-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: multi-overlay-skill
version: 1.0.0
description: multi overlay
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Overlay prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: multi-overlay-skill
version: 1.0.0
description: multi overlay
entrypoint: system_prompt
capabilities: ["pkg"]
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
    - provider: openai
      model: gpt-4o
      path: agents/openai.gpt-4o.yaml
""")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("system_prompt: provider overlay\n")
        with open(os.path.join(pkg_dir, "agents", "openai.gpt-4o.yaml"), "w") as f:
            f.write("instructions: model overlay\n")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        validation = SkillLoader.validate_package(package)
        assert validation.is_valid is True

def test_skill_loader_validate_package_rejects_invalid_overlay_yaml():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "yaml-skill")
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: yaml-skill
version: 1.0.0
description: yaml
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Yaml prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: yaml-skill
version: 1.0.0
description: yaml
entrypoint: system_prompt
capabilities: ["pkg"]
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
""")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("system_prompt: [broken\n")

        package = SkillLoader.parse_package(pkg_dir)
        assert package is not None
        validation = SkillLoader.validate_package(package)
        assert validation.is_valid is False
        assert "Declared overlay yaml is invalid: agents/openai.yaml" in validation.errors

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


def test_skill_router_uses_injected_skill_group_store():
    registry = SkillRegistry()
    registry.register(
        SkillSpec(
            name="group-skill",
            version="1.0.0",
            description="group skill",
            capabilities=["group"],
            entrypoint="system_prompt",
            system_prompt="group",
            os=[platform.system().lower()],
        )
    )
    fake_group_store = type(
        "FakeGroupStore",
        (),
        {"get_skill_refs_by_group_ids": lambda self, group_ids: ["group-skill:1.0.0"] if group_ids == ["g1"] else []},
    )()
    router = SkillRouter(registry, skill_group_store=fake_group_store)
    agent = type(
        "Agent",
        (),
        {
            "skill_groups": ["g1"],
            "resolved_visible_skills": [],
            "extra_visible_skills": [],
            "visible_skills": [],
        },
    )()

    visible = router.get_visible_skills(agent)

    assert len(visible) == 1
    assert visible[0].name == "group-skill"


def test_markdown_skill_adapter_descriptor_includes_prompt_blocks_and_constraints():
    skill = SkillSpec(
        name="adapter-skill",
        version="1.0.0",
        description="adapter",
        capabilities=["adapter"],
        entrypoint="system_prompt",
        system_prompt="System prompt",
        instructions="Follow instructions",
        examples="Example block",
        failure_handling="Retry safely",
        constraints=SkillConstraints(allowed_tools=["builtin:docs_read"], timeout=30),
    )

    descriptor = MarkdownSkillAdapter.to_descriptor(skill)

    assert descriptor.prompt_blocks["system_prompt"] == "System prompt"
    assert descriptor.prompt_blocks["instructions"] == "Follow instructions"
    assert descriptor.prompt_blocks["examples"] == "Example block"
    assert descriptor.prompt_blocks["failure_handling"] == "Retry safely"
    assert descriptor.tool_policy["allowed_tools"] == ["builtin:docs_read"]
    assert descriptor.constraints["timeout"] == 30

def test_markdown_skill_adapter_descriptor_includes_action_descriptors():
    skill = SkillSpec(
        name="action-adapter-skill",
        version="1.0.0",
        description="adapter",
        capabilities=["adapter"],
        entrypoint="system_prompt",
        system_prompt="System prompt",
        metadata={
            "package_actions": [
                {
                    "id": "generate",
                    "tool": "builtin:docs_read",
                    "resource": "scripts-generate.py",
                    "path": "scripts/generate.py",
                    "runtime": "python",
                    "load_tier": "action",
                    "safety": "workspace_write",
                    "approval_policy": "manual",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "metadata": {"label": "Generate"},
                }
            ]
        },
    )

    descriptor = MarkdownSkillAdapter.to_descriptor(skill)

    assert len(descriptor.actions) == 1
    action = descriptor.actions[0]
    assert action.id == "generate"
    assert action.name == "action-adapter-skill"
    assert action.version == "1.0.0"
    assert action.tool == "builtin:docs_read"
    assert action.path == "scripts/generate.py"
    assert action.runtime == "python"
    assert action.approval_policy == "manual"
    assert action.metadata["label"] == "Generate"

def test_skill_registry_exposes_runtime_action_descriptors():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(pkg_dir, "agents"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:docs_read
    resource: generate
    approval_policy: manual
    input_schema:
      type: object
overlays:
  providers:
    - provider: openai
      path: agents/openai.yaml
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")
        with open(os.path.join(pkg_dir, "agents", "openai.yaml"), "w") as f:
            f.write("""metadata:
  overlay_mode: openai
""")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        actions = registry.get_action_descriptors("action-skill")
        assert len(actions) == 1
        action = actions[0]
        assert action.id == "generate"
        assert action.name == "action-skill"
        assert action.tool == "builtin:docs_read"
        assert action.path == "scripts/generate.py"
        assert action.runtime == "python"
        assert action.safety == "workspace_write"
        assert action.approval_policy == "manual"
        assert action.input_schema == {"type": "object"}

        overlaid_actions = registry.get_action_descriptors("action-skill", provider="openai", model_name="gpt-4o")
        assert len(overlaid_actions) == 1
        assert overlaid_actions[0].id == "generate"

        full_skill = registry.get_full_skill("action-skill")
        assert full_skill is not None
        descriptor = MarkdownSkillAdapter.to_descriptor(full_skill)
        assert len(descriptor.actions) == 1
        assert descriptor.actions[0].id == "generate"

def test_skill_policy_gate_validates_action_invocation_tool_only():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        safety="workspace_write",
        approval_policy="manual",
    )

    result = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])

    assert result.accepted is True
    assert result.execution_mode == "tool_only"
    assert result.approval_required is True
    assert result.mapped_tool == "builtin:docs_read"
    assert result.validation_errors == []
    assert result.missing_requirements == []

def test_skill_policy_gate_rejects_action_invocation_when_required_tool_missing():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        safety="workspace_write",
        approval_policy="manual",
    )

    result = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_search"])

    assert result.accepted is False
    assert result.mapped_tool == "builtin:docs_read"
    assert result.missing_requirements == ["tool:builtin:docs_read"]

def test_skill_policy_gate_allows_builtin_exec_binding_as_platform_tool():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        safety="workspace_write",
        approval_policy="manual",
    )

    result = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:exec"])

    assert result.accepted is True
    assert result.mapped_tool == "builtin:exec"
    assert result.execution_mode == "tool_only"
    assert result.validation_errors == []

def test_skill_policy_gate_requires_approval_for_browser_write_actions():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
                "binding_dom_version": {"type": "string"},
                "active_dom_version": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
            "required": ["status"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": [
                    "session_id",
                    "tab_id",
                    "binding_source",
                    "binding_session_id",
                    "binding_tab_id",
                    "binding_dom_version",
                    "active_dom_version",
                ],
            },
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "element_ref": "snapshot:browser_snapshot#node:1",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
        },
    )

    assert result.accepted is True
    assert result.approval_required is True
    assert result.mapped_tool == "builtin:browser_click"
    assert result.metadata["validated_arguments"] == {
        "session_id": "session-1",
        "tab_id": "tab-1",
        "element_ref": "snapshot:browser_snapshot#node:1",
        "binding_source": "snapshot:browser_snapshot",
        "binding_session_id": "session-1",
        "binding_tab_id": "tab-1",
    }
    assert result.metadata["tool_family"] == "agent_browser"
    assert result.metadata["operation"] == "click"
    assert result.metadata["browser_continuity"] == {
        "contract_mode": "authoritative_target_mutation",
        "current_execution_mode": "resumable_session_required",
        "authoritative_target_required": True,
        "resumable_continuity": "deferred",
    }
    assert result.metadata["browser_continuity_resolution"] == {
        "resolver_contract_version": 1,
        "resolution_mode": "session_tab_target_lookup",
        "continuity_status": "resolver_deferred",
        "session_lookup_required": True,
        "tab_lookup_required": True,
        "target_lookup_required": True,
        "provided_context": {
            "has_url": False,
            "has_session_id": True,
            "has_tab_id": True,
            "has_element_ref": True,
        },
        "missing_context": [],
        "contract_mode": "authoritative_target_mutation",
    }
    assert result.metadata["runtime_metadata"] == {
        "operation": "click",
        "tool_family": "agent_browser",
        "mapped_tool": "builtin:browser_click",
        "session_id": "session-1",
        "tab_id": "tab-1",
        "element_ref": "snapshot:browser_snapshot#node:1",
        "binding_source": "snapshot:browser_snapshot",
        "binding_session_id": "session-1",
        "binding_tab_id": "tab-1",
    }

def test_skill_policy_gate_blocks_browser_click_without_authoritative_target_context():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        input_schema={
            "type": "object",
            "properties": {
                "element_ref": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": ["session_id", "tab_id", "binding_source", "binding_session_id", "binding_tab_id"],
            },
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={"element_ref": "button:submit"},
    )

    assert result.accepted is False
    assert result.approval_required is True
    assert result.validation_errors == [
        "browser_session_required",
        "browser_tab_required",
        "browser_target_required",
    ]

def test_skill_policy_gate_blocks_browser_click_when_target_is_stale():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
                "binding_dom_version": {"type": "string"},
                "active_dom_version": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": [
                    "session_id",
                    "tab_id",
                    "binding_source",
                    "binding_session_id",
                    "binding_tab_id",
                    "binding_dom_version",
                    "active_dom_version",
                ],
            },
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "element_ref": "snapshot:browser_snapshot#node:1",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
            "binding_dom_version": "dom:v1",
            "active_dom_version": "dom:v2",
        },
    )

    assert result.accepted is False
    assert result.validation_errors == ["browser_target_stale"]

def test_skill_policy_gate_blocks_browser_click_when_element_ref_is_not_platform_minted():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": [
                    "session_id",
                    "tab_id",
                    "binding_source",
                    "binding_session_id",
                    "binding_tab_id",
                ],
            },
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "element_ref": "node:1",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
        },
    )

    assert result.accepted is False
    assert result.validation_errors == ["browser_target_context_mismatch"]

def test_skill_policy_gate_keeps_browser_open_auto_approved_and_runtime_metadata_ready():
    action = RuntimeSkillActionDescriptor(
        id="open_page",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_open",
        approval_policy="auto",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "open",
            "runtime_metadata_expectations": {
                "required": ["operation", "url"],
                "optional": ["session_id", "tab_id"],
            },
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_open"],
        arguments={"url": "https://example.com", "session_id": "session-1"},
    )

    assert result.accepted is True
    assert result.approval_required is False
    assert result.mapped_tool == "builtin:browser_open"
    assert result.metadata["browser_continuity"] == {
        "contract_mode": "single_use_url_scoped",
        "current_execution_mode": "single_use_url_scoped",
        "authoritative_target_required": False,
        "resumable_continuity": "not_required",
    }
    assert result.metadata["browser_continuity_resolution"] == {
        "resolver_contract_version": 1,
        "resolution_mode": "single_use_url",
        "continuity_status": "single_use_ready",
        "session_lookup_required": False,
        "tab_lookup_required": False,
        "target_lookup_required": False,
        "provided_context": {
            "has_url": True,
            "has_session_id": True,
            "has_tab_id": False,
            "has_element_ref": False,
        },
        "missing_context": [],
    }
    assert result.metadata["runtime_metadata"] == {
        "operation": "open",
        "tool_family": "agent_browser",
        "mapped_tool": "builtin:browser_open",
        "url": "https://example.com",
        "session_id": "session-1",
    }

def test_skill_policy_gate_validates_action_arguments_against_input_schema():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_s": {"type": "integer", "default": 30},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={"command": "pwd"},
    )

    assert result.accepted is True
    assert result.validation_errors == []
    assert result.metadata["validated_arguments"] == {"command": "pwd", "timeout_s": 30}

def test_skill_policy_gate_rejects_missing_required_action_argument():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={},
    )

    assert result.accepted is False
    assert result.validation_errors == ["Missing required action argument: command"]

def test_skill_policy_gate_rejects_unexpected_action_argument():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={"command": "pwd", "unsafe": True},
    )

    assert result.accepted is False
    assert result.validation_errors == ["Unexpected action argument: unsafe"]

def test_skill_policy_gate_validates_nested_action_arguments_and_applies_defaults():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "options": {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string"},
                        "shell": {"type": "string", "default": "bash"},
                    },
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
                "targets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "mode": {"type": "string", "enum": ["read", "write"]},
                        },
                        "required": ["path", "mode"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["command", "options"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={
            "command": "ls",
            "options": {"cwd": "/workspace"},
            "targets": [{"path": "docs", "mode": "read"}],
        },
    )

    assert result.accepted is True
    assert result.validation_errors == []
    assert result.metadata["validated_arguments"] == {
        "command": "ls",
        "options": {"cwd": "/workspace", "shell": "bash"},
        "targets": [{"path": "docs", "mode": "read"}],
    }

def test_skill_policy_gate_reports_nested_argument_paths():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "options": {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string"},
                    },
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
                "targets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "mode": {"type": "string", "enum": ["read", "write"]},
                        },
                        "required": ["path", "mode"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["options"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={
            "options": {"extra": True},
            "targets": [{"path": "docs", "mode": "delete"}],
        },
    )

    assert result.accepted is False
    assert result.validation_errors == [
        "Missing required action argument: options.cwd",
        "Unexpected action argument: options.extra",
        "Invalid value for action argument `targets[0].mode`: expected one of ['read', 'write']",
    ]

def test_skill_policy_gate_accepts_nullable_arguments_and_type_list_null():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "note": {"type": "string", "nullable": True},
                "metadata": {"type": ["object", "null"]},
            },
            "required": ["command", "note"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={"command": "pwd", "note": None, "metadata": None},
    )

    assert result.accepted is True
    assert result.validation_errors == []
    assert result.metadata["validated_arguments"] == {
        "command": "pwd",
        "note": None,
        "metadata": None,
    }

def test_skill_policy_gate_rejects_null_for_non_nullable_argument():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={"command": None},
    )

    assert result.accepted is False
    assert result.validation_errors == ["Invalid type for action argument `command`: expected string"]

def test_skill_policy_gate_enforces_string_numeric_and_array_constraints():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 5,
                    "pattern": "^[a-z]+$",
                },
                "timeout_s": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 60,
                },
                "targets": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 2,
                    "items": {"type": "string", "minLength": 2},
                },
            },
            "required": ["command", "timeout_s", "targets"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={
            "command": "AB",
            "timeout_s": 0,
            "targets": ["x", "ok", "extra"],
        },
    )

    assert result.accepted is False
    assert result.validation_errors == [
        "String action argument `command` must have length >= 3",
        "String action argument `command` must match pattern `^[a-z]+$`",
        "Numeric action argument `timeout_s` must be >= 1",
        "Array action argument `targets` must have at most 2 item(s)",
        "String action argument `targets[0]` must have length >= 2",
    ]

def test_skill_policy_gate_applies_constraints_with_nested_paths():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:exec",
        input_schema={
            "type": "object",
            "properties": {
                "options": {
                    "type": "object",
                    "properties": {
                        "cwd": {
                            "type": "string",
                            "minLength": 4,
                            "pattern": "^/",
                        },
                    },
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
                "targets": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "retries": {"type": "integer", "minimum": 1, "maximum": 3},
                        },
                        "required": ["retries"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["options", "targets"],
            "additionalProperties": False,
        },
    )

    result = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:exec"],
        arguments={
            "options": {"cwd": "tmp"},
            "targets": [{"retries": 0}],
        },
    )

    assert result.accepted is False
    assert result.validation_errors == [
        "String action argument `options.cwd` must have length >= 4",
        "String action argument `options.cwd` must match pattern `^/`",
        "Numeric action argument `targets[0].retries` must be >= 1",
    ]

def test_skill_registry_validates_action_invocation_request():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:docs_read
    resource: generate
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        result = registry.validate_action_invocation(
            RuntimeSkillActionInvocationRequest(
                skill_name="action-skill",
                skill_version="1.0.0",
                action_id="generate",
                provider="openai",
                model_name="gpt-4o",
                arguments={"topic": "quarterly report"},
                enabled_tools=["builtin:docs_read"],
            )
        )

        assert result.accepted is True
        assert result.execution_mode == "tool_only"
        assert result.approval_required is True
        assert result.mapped_tool == "builtin:docs_read"
        assert result.metadata["provider"] == "openai"
        assert result.metadata["model_name"] == "gpt-4o"
        assert result.metadata["argument_keys"] == ["topic"]

def test_skill_registry_validates_action_invocation_request_for_builtin_exec():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "exec-action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: exec-action-skill
version: 1.0.0
description: exec action skill
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Exec action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: exec-action-skill
version: 1.0.0
description: exec action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: exec_task
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: exec_task
    tool: builtin:exec
    resource: exec_task
    input_schema:
      type: object
      properties:
        command:
          type: string
        working_dir:
          type: string
      required: ["command"]
      additionalProperties: false
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('exec task')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        result = registry.validate_action_invocation(
            RuntimeSkillActionInvocationRequest(
                skill_name="exec-action-skill",
                skill_version="1.0.0",
                action_id="exec_task",
                provider="openai",
                model_name="gpt-4o",
                arguments={"command": "pwd"},
                enabled_tools=["builtin:exec"],
            )
        )

        assert result.accepted is True
        assert result.execution_mode == "tool_only"
        assert result.approval_required is True
        assert result.mapped_tool == "builtin:exec"
        assert result.validation_errors == []
        assert result.missing_requirements == []
        assert result.metadata["validated_arguments"] == {"command": "pwd"}

def test_skill_registry_preserves_browser_action_contract_fields():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "browser-operator")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: browser-operator
version: 1.0.0
description: browser operator skill
capabilities: ["browser"]
entrypoint: system_prompt
---
## System Prompt
Browser operator prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: browser-operator
version: 1.0.0
description: browser operator skill
entrypoint: system_prompt
capabilities: ["browser"]
resources:
  scripts:
    - id: click_element
      path: scripts/click.py
      runtime: python
      safety: browser_write
actions:
  - id: click_element
    tool: builtin:browser_click
    resource: click_element
    safety: browser_write
    approval_policy: manual
    input_schema:
      type: object
      properties:
        session_id:
          type: string
        tab_id:
          type: string
        element_ref:
          type: string
      required: ["element_ref"]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        status:
          type: string
        browser_context:
          type: object
      required: ["status", "browser_context"]
      additionalProperties: false
    metadata:
      tool_family: agent_browser
      operation: click
      runtime_metadata_expectations:
        required: ["operation", "element_ref"]
        optional: ["session_id", "tab_id"]
""")
        with open(os.path.join(pkg_dir, "scripts", "click.py"), "w") as f:
            f.write("print('click')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()

        actions = registry.get_action_descriptors("browser-operator")

        assert len(actions) == 1
        assert actions[0].tool == "builtin:browser_click"
        assert actions[0].safety == "browser_write"
        assert actions[0].approval_policy == "manual"
        assert actions[0].input_schema["required"] == ["element_ref"]
        assert actions[0].output_schema["required"] == ["status", "browser_context"]
        assert actions[0].metadata["tool_family"] == "agent_browser"
        assert actions[0].metadata["runtime_metadata_expectations"]["required"] == [
            "operation",
            "element_ref",
        ]

def test_skill_registry_loads_builtin_browser_operator_package():
    registry = SkillRegistry(skill_dirs=["backend/data/skills"])
    registry.load_all()

    package = registry.get_package_manifest("browser-operator")
    assert package is not None
    assert package.name == "browser-operator"
    assert len(package.actions) == 6

    action_ids = {action.id for action in package.actions}
    assert action_ids == {
        "open_page",
        "snapshot_page",
        "click_element",
        "type_into_field",
        "press_key",
        "capture_screenshot",
    }

    click_action = next(action for action in package.actions if action.id == "click_element")
    assert click_action.tool == "builtin:browser_click"
    assert click_action.safety == "browser_write"
    assert click_action.metadata["tool_family"] == "agent_browser"
    assert "binding_source" in click_action.input_schema["properties"]
    assert click_action.metadata["runtime_metadata_expectations"]["optional"] == [
        "session_id",
        "tab_id",
        "url",
        "binding_source",
        "binding_session_id",
        "binding_tab_id",
        "binding_url",
        "binding_dom_version",
        "active_dom_version",
    ]
    assert click_action.metadata["structured_failure_codes"] == [
        "browser_session_required",
        "browser_tab_required",
        "browser_target_required",
        "browser_target_stale",
        "browser_target_context_mismatch",
    ]

    press_action = next(action for action in package.actions if action.id == "press_key")
    assert press_action.tool == "builtin:browser_press"
    assert "url" in press_action.input_schema["properties"]
    assert press_action.input_schema["required"] == ["url", "key"]
    assert press_action.metadata["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
        "key",
    ]
    assert press_action.metadata["runtime_metadata_expectations"]["optional"] == [
        "session_id",
        "tab_id",
        "url",
        "wait_until",
        "element_ref",
    ]

    snapshot_action = next(action for action in package.actions if action.id == "snapshot_page")
    assert snapshot_action.tool == "builtin:browser_snapshot"
    assert snapshot_action.input_schema["required"] == ["url"]
    assert snapshot_action.metadata["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
    ]

    screenshot_action = next(action for action in package.actions if action.id == "capture_screenshot")
    assert screenshot_action.tool == "builtin:browser_screenshot"
    assert screenshot_action.input_schema["required"] == ["url"]
    assert screenshot_action.metadata["runtime_metadata_expectations"]["required"] == [
        "operation",
        "url",
    ]

def test_skill_action_execution_service_preflight_carries_browser_runtime_contract_metadata():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        approval_policy="manual",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": ["session_id", "tab_id", "binding_source", "binding_session_id", "binding_tab_id"],
            },
        },
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "element_ref": "button:submit",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
        },
    )
    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )()
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "button:submit",
                    "binding_source": "snapshot:browser_snapshot",
                    "binding_session_id": "session-1",
                    "binding_tab_id": "tab-1",
                },
                enabled_tools=["builtin:browser_click"],
            )
        )
    )

    fallback = service.build_transition_result(
        invocation=invocation,
        status="queued",
        request_id="req-browser",
        lifecycle_phase="execution",
        metadata={
            "tool_family": invocation.metadata.get("tool_family"),
            "operation": invocation.metadata.get("operation"),
            "runtime_metadata_expectations": invocation.metadata.get("runtime_metadata_expectations"),
            "runtime_metadata": invocation.metadata.get("runtime_metadata"),
        },
    )

    assert result.metadata["tool_family"] == "agent_browser"
    assert result.metadata["operation"] == "click"
    assert result.metadata["runtime_metadata"]["element_ref"] == "button:submit"
    assert result.metadata["runtime_metadata"]["session_id"] == "session-1"
    assert result.metadata["runtime_metadata"]["tab_id"] == "tab-1"
    assert result.metadata["runtime_metadata"]["binding_source"] == "snapshot:browser_snapshot"
    assert result.metadata["browser_continuity"] == {
        "contract_mode": "authoritative_target_mutation",
        "current_execution_mode": "resumable_session_required",
        "authoritative_target_required": True,
        "resumable_continuity": "deferred",
    }
    assert result.metadata["browser_continuity_resolution"]["resolution_mode"] == "explicit_request_context"
    assert result.metadata["browser_continuity_resolution"]["session_lookup_required"] is False
    assert result.metadata["browser_continuity_resolution"]["target_lookup_required"] is False
    assert result.metadata["browser_continuity_resolver"] == {
        "resolver_id": "explicit_context",
        "status": "resolved",
        "resolved": True,
    }
    assert result.metadata["browser_continuity_resolution"]["continuity_status"] == "resolved"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["session_id"] == "session-1"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["tab_id"] == "tab-1"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["element_ref"] == "button:submit"
    assert fallback.metadata["runtime_metadata"]["mapped_tool"] == "builtin:browser_click"


def test_skill_action_execution_service_preflight_carries_browser_target_binding_metadata():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        approval_policy="manual",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_tab_id": {"type": "string"},
                "binding_url": {"type": "string"},
                "binding_dom_version": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": [
                    "session_id",
                    "tab_id",
                    "binding_source",
                    "binding_session_id",
                    "binding_tab_id",
                    "binding_url",
                    "binding_dom_version",
                ],
            },
        },
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "element_ref": "node:1",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
            "binding_url": "https://example.com/",
            "binding_dom_version": "dom:v1",
        },
    )
    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )()
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser-binding",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "node:1",
                    "binding_source": "snapshot:browser_snapshot",
                    "binding_session_id": "session-1",
                    "binding_tab_id": "tab-1",
                    "binding_url": "https://example.com/",
                    "binding_dom_version": "dom:v1",
                },
                enabled_tools=["builtin:browser_click"],
            )
        )
    )

    assert result.metadata["runtime_metadata"]["binding_source"] == "snapshot:browser_snapshot"
    assert result.metadata["runtime_metadata"]["binding_session_id"] == "session-1"
    assert result.metadata["runtime_metadata"]["binding_tab_id"] == "tab-1"
    assert result.metadata["runtime_metadata"]["binding_url"] == "https://example.com/"
    assert result.metadata["runtime_metadata"]["binding_dom_version"] == "dom:v1"
    assert result.metadata["browser_continuity"]["contract_mode"] == "authoritative_target_mutation"
    assert result.metadata["browser_continuity"]["resumable_continuity"] == "deferred"
    assert result.metadata["browser_continuity_resolution"]["contract_mode"] == "authoritative_target_mutation"
    assert result.metadata["browser_continuity_resolution"]["continuity_status"] == "resolved"
    assert result.metadata["browser_continuity_resolution"]["resolution_mode"] == "explicit_request_context"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["session_id"] == "session-1"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["tab_id"] == "tab-1"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["element_ref"] == "node:1"
    assert result.metadata["browser_continuity_resolver"] == {
        "resolver_id": "explicit_context",
        "status": "resolved",
        "resolved": True,
    }

def test_skill_action_execution_service_preflight_uses_injected_browser_continuity_resolver():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        approval_policy="manual",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "url": {"type": "string"},
                "element_ref": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": [
                    "session_id",
                    "tab_id",
                    "url",
                    "binding_source",
                    "binding_session_id",
                    "binding_tab_id",
                ],
            },
        },
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "url": "https://example.com",
            "element_ref": "snapshot:browser_snapshot#node:1",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
        },
    )

    class StubResolver:
        def resolve(self, request):
            assert request.browser_continuity["contract_mode"] == "authoritative_target_mutation"
            return RuntimeBrowserContinuityResolutionResult(
                resolver_id="stub_resolver",
                status="resolved",
                resolved=True,
                metadata={
                    "resolver_contract_version": 1,
                    "resolution_mode": "stubbed_session_lookup",
                    "continuity_status": "resolved",
                    "session_lookup_required": True,
                    "tab_lookup_required": True,
                    "target_lookup_required": True,
                    "provided_context": request.browser_continuity_resolution.get("provided_context", {}),
                    "missing_context": [],
                },
            )

    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )(),
        continuity_resolver=StubResolver(),
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser-resolver",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "url": "https://example.com",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                    "binding_session_id": "session-1",
                    "binding_tab_id": "tab-1",
                },
                enabled_tools=["builtin:browser_click"],
            )
        )
    )

    assert result.metadata["browser_continuity_resolver"] == {
        "resolver_id": "stub_resolver",
        "status": "resolved",
        "resolved": True,
    }
    assert result.metadata["browser_continuity_resolution"]["resolution_mode"] == "stubbed_session_lookup"
    assert result.metadata["browser_continuity_resolution"]["continuity_status"] == "resolved"


def test_default_browser_continuity_resolver_preserves_deferred_metadata():
    resolver = DefaultBrowserContinuityResolver()
    request = RuntimeSkillActionExecutionRequest(
        request_id="req-default-resolver",
        invocation=RuntimeSkillActionInvocationRequest(
            skill_name="browser-operator",
            skill_version="1.0.0",
            action_id="click_element",
            arguments={},
            enabled_tools=["builtin:browser_click"],
        ),
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=True,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        approval_required=True,
        approval_policy="manual",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "tab_id": "tab-1",
                "element_ref": "snapshot:browser_snapshot#node:1",
            },
        },
    )

    result = resolver.resolve(
        RuntimeBrowserContinuityResolutionRequest(
            invocation_request=request.invocation,
            invocation_result=invocation,
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={
                "resolver_contract_version": 1,
                "resolution_mode": "session_tab_target_lookup",
                "continuity_status": "resolver_deferred",
                "session_lookup_required": True,
                "tab_lookup_required": True,
                "target_lookup_required": True,
                "provided_context": {
                    "has_url": False,
                    "has_session_id": True,
                    "has_tab_id": True,
                    "has_element_ref": True,
                },
                "missing_context": [],
                "contract_mode": "authoritative_target_mutation",
            },
        )
    )

    assert result.resolver_id == "default_noop"
    assert result.status == "deferred"
    assert result.resolved is False
    assert result.metadata["continuity_status"] == "resolver_deferred"
    assert "resolved_context" not in result.metadata


def test_default_browser_continuity_lookup_backend_returns_not_configured():
    backend = DefaultBrowserContinuityLookupBackend()
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={},
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            browser_continuity={},
            browser_continuity_resolution={},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.backend_id == "default_noop"
    assert result.status == "not_configured"
    assert result.resolved is False
    assert result.metadata == {}


def test_explicit_context_browser_continuity_resolver_returns_resolved_context():
    resolver = ExplicitContextBrowserContinuityResolver()
    invocation = RuntimeSkillActionInvocationResult(
        accepted=True,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="type_into_field",
        approval_required=True,
        approval_policy="manual",
        mapped_tool="builtin:browser_type",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "type",
            "validated_arguments": {
                "session_id": "session-1",
                "tab_id": "tab-1",
                "element_ref": "snapshot:browser_snapshot#node:2",
                "binding_source": "snapshot:browser_snapshot",
                "binding_session_id": "session-1",
                "binding_tab_id": "tab-1",
            },
        },
    )

    result = resolver.resolve(
        RuntimeBrowserContinuityResolutionRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="type_into_field",
                arguments={},
                enabled_tools=["builtin:browser_type"],
            ),
            invocation_result=invocation,
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={
                "resolver_contract_version": 1,
                "resolution_mode": "session_tab_target_lookup",
                "continuity_status": "resolver_deferred",
                "session_lookup_required": True,
                "tab_lookup_required": True,
                "target_lookup_required": True,
                "provided_context": {
                    "has_url": False,
                    "has_session_id": True,
                    "has_tab_id": True,
                    "has_element_ref": True,
                },
                "missing_context": [],
                "contract_mode": "authoritative_target_mutation",
            },
        )
    )

    assert result.resolver_id == "explicit_context"
    assert result.status == "resolved"
    assert result.resolved is True
    assert result.metadata["resolution_mode"] == "explicit_request_context"
    assert result.metadata["continuity_status"] == "resolved"
    assert result.metadata["session_lookup_required"] is False
    assert result.metadata["tab_lookup_required"] is False
    assert result.metadata["target_lookup_required"] is False
    assert result.metadata["resolved_context"] == {
        "resolved_context_id": result.metadata["resolved_context"]["resolved_context_id"],
        "session_id": "session-1",
        "tab_id": "tab-1",
        "element_ref": "snapshot:browser_snapshot#node:2",
        "resolution_mode": "explicit_request_context",
        "resolution_source": "explicit_request_context",
        "resolved_target_kind": "authoritative_target",
    }


def test_explicit_context_browser_continuity_resolver_blocks_when_context_missing():
    resolver = ExplicitContextBrowserContinuityResolver()
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        approval_required=True,
        approval_policy="manual",
        mapped_tool="builtin:browser_click",
        validation_errors=["browser_tab_required"],
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "element_ref": "snapshot:browser_snapshot#node:1",
            },
        },
    )

    result = resolver.resolve(
        RuntimeBrowserContinuityResolutionRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={
                "resolver_contract_version": 1,
                "resolution_mode": "session_tab_target_lookup",
                "continuity_status": "resolver_deferred",
                "session_lookup_required": True,
                "tab_lookup_required": True,
                "target_lookup_required": True,
                "provided_context": {
                    "has_url": False,
                    "has_session_id": True,
                    "has_tab_id": False,
                    "has_element_ref": True,
                },
                "missing_context": ["tab_id"],
                "contract_mode": "authoritative_target_mutation",
            },
        )
    )

    assert result.resolver_id == "explicit_context"
    assert result.status == "blocked"
    assert result.resolved is False
    assert result.metadata["continuity_status"] == "blocked"
    assert result.metadata["missing_context"] == ["tab_id"]
    assert result.metadata["resolved_context"] == {}
    assert result.metadata["lookup_backend"] == {
        "backend_id": "default_noop",
        "status": "not_configured",
        "resolved": False,
    }


def test_explicit_context_browser_continuity_resolver_can_use_lookup_backend_stub():
    invocation = RuntimeSkillActionInvocationResult(
        accepted=True,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        approval_required=True,
        approval_policy="manual",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "binding_source": "snapshot:browser_snapshot",
            },
        },
    )

    class StubLookupBackend:
        def lookup(self, request):
            assert request.missing_context == ["tab_id", "element_ref"]
            return RuntimeBrowserContinuityLookupResult(
                backend_id="stub_lookup",
                status="resolved",
                resolved=True,
                metadata={
                    "resolution_mode": "lookup_backend",
                    "continuity_status": "resolved",
                    "resolved_context": {
                        "resolved_context_id": "browser_ctx:lookup",
                        "session_id": "session-1",
                        "tab_id": "tab-1",
                        "element_ref": "snapshot:browser_snapshot#node:1",
                        "resolution_mode": "lookup_backend",
                        "resolution_source": "lookup_backend",
                        "resolved_target_kind": "authoritative_target",
                    },
                },
            )

    resolver = ExplicitContextBrowserContinuityResolver(lookup_backend=StubLookupBackend())
    result = resolver.resolve(
        RuntimeBrowserContinuityResolutionRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={
                "resolver_contract_version": 1,
                "resolution_mode": "session_tab_target_lookup",
                "continuity_status": "resolver_deferred",
                "session_lookup_required": True,
                "tab_lookup_required": True,
                "target_lookup_required": True,
                "provided_context": {
                    "has_url": False,
                    "has_session_id": True,
                    "has_tab_id": False,
                    "has_element_ref": False,
                },
                "missing_context": ["tab_id", "element_ref"],
                "contract_mode": "authoritative_target_mutation",
            },
        )
    )

    assert result.resolver_id == "explicit_context"
    assert result.status == "resolved"
    assert result.resolved is True
    assert result.metadata["resolution_mode"] == "lookup_backend"
    assert result.metadata["continuity_status"] == "resolved"
    assert result.metadata["resolved_context"]["tab_id"] == "tab-1"
    assert result.metadata["resolved_context"]["element_ref"] == "snapshot:browser_snapshot#node:1"
    assert result.metadata["lookup_backend"] == {
        "backend_id": "stub_lookup",
        "status": "resolved",
        "resolved": True,
    }


def test_yue_action_state_browser_continuity_lookup_backend_returns_not_found_without_matching_record():
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(list_action_states_by_request_id=lambda *args, **kwargs: [])
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "binding_source": "snapshot:browser_snapshot",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id="req-browser-missing",
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.backend_id == "yue_action_state"
    assert result.status == "not_found"
    assert result.resolved is False
    assert result.metadata["reason"] == "action_state_not_found"
    assert result.metadata["lookup_request_id"] == "req-browser-missing"


def test_yue_action_state_browser_continuity_lookup_backend_returns_not_found_without_request_id():
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(list_action_states_by_request_id=lambda *args, **kwargs: [])
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "binding_source": "snapshot:browser_snapshot",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id=None,
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.backend_id == "yue_action_state"
    assert result.status == "not_found"
    assert result.resolved is False
    assert result.metadata["reason"] == "request_id_unavailable"


def test_yue_action_state_browser_continuity_lookup_backend_resolves_from_persisted_action_state():
    persisted_state = SimpleNamespace(
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                    "binding_session_id": "session-1",
                    "binding_tab_id": "tab-1",
                },
                "browser_continuity_resolution": {
                    "continuity_status": "resolved",
                    "resolved_context": {
                        "resolved_context_id": "browser_ctx:prior",
                        "session_id": "session-1",
                        "tab_id": "tab-1",
                        "element_ref": "snapshot:browser_snapshot#node:1",
                        "resolution_mode": "explicit_request_context",
                        "resolution_source": "explicit_request_context",
                        "resolved_target_kind": "authoritative_target",
                    },
                },
            },
        },
    )
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(
            list_action_states_by_request_id=lambda *args, **kwargs: [persisted_state]
        )
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "binding_source": "snapshot:browser_snapshot",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id="req-browser-resume",
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.backend_id == "yue_action_state"
    assert result.status == "resolved"
    assert result.resolved is True
    assert result.metadata["resolution_mode"] == "action_state_lookup"
    assert result.metadata["resolved_context"]["session_id"] == "session-1"
    assert result.metadata["resolved_context"]["tab_id"] == "tab-1"
    assert result.metadata["resolved_context"]["element_ref"] == "snapshot:browser_snapshot#node:1"
    assert result.metadata["resolved_context"]["resolution_source"] == "yue_action_state_lookup"


def test_yue_action_state_browser_continuity_lookup_backend_blocks_on_binding_source_mismatch():
    persisted_state = SimpleNamespace(
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                },
            },
        },
    )
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(
            list_action_states_by_request_id=lambda *args, **kwargs: [persisted_state]
        )
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "binding_source": "snapshot:other_snapshot",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id="req-browser-mismatch",
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.backend_id == "yue_action_state"
    assert result.status == "blocked"
    assert result.resolved is False
    assert result.metadata["reason"] == "binding_source_mismatch"
    assert result.metadata["record_source"]["request_id"] == "req-browser-mismatch"


def test_yue_action_state_browser_continuity_lookup_backend_prefers_continuity_bearing_record():
    sparse_state = SimpleNamespace(
        id=2,
        lifecycle_phase="execution",
        lifecycle_status="running",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "binding_source": "snapshot:browser_snapshot",
                },
            },
        },
    )
    continuity_state = SimpleNamespace(
        id=1,
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                },
                "browser_continuity_resolution": {
                    "continuity_status": "resolved",
                    "resolved_context": {
                        "resolved_context_id": "browser_ctx:prior",
                        "session_id": "session-1",
                        "tab_id": "tab-1",
                        "element_ref": "snapshot:browser_snapshot#node:1",
                        "resolution_mode": "explicit_request_context",
                        "resolution_source": "explicit_request_context",
                        "resolved_target_kind": "authoritative_target",
                    },
                },
            },
        },
    )
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(
            list_action_states_by_request_id=lambda *args, **kwargs: [sparse_state, continuity_state]
        )
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "binding_source": "snapshot:browser_snapshot",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id="req-browser-best-record",
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.status == "resolved"
    assert result.metadata["record_source"]["lifecycle_phase"] == "preflight"
    assert result.metadata["resolved_context"]["tab_id"] == "tab-1"


def test_yue_action_state_browser_continuity_lookup_backend_prefers_binding_compatible_record():
    mismatched_better_state = SimpleNamespace(
        id=3,
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-99",
                    "element_ref": "snapshot:other_snapshot#node:9",
                    "binding_source": "snapshot:other_snapshot",
                },
                "browser_continuity_resolution": {
                    "continuity_status": "resolved",
                    "resolved_context": {
                        "resolved_context_id": "browser_ctx:other",
                        "session_id": "session-1",
                        "tab_id": "tab-99",
                        "element_ref": "snapshot:other_snapshot#node:9",
                        "resolution_mode": "explicit_request_context",
                        "resolution_source": "explicit_request_context",
                        "resolved_target_kind": "authoritative_target",
                    },
                },
            },
        },
    )
    matching_state = SimpleNamespace(
        id=2,
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                },
            },
        },
    )
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(
            list_action_states_by_request_id=lambda *args, **kwargs: [
                mismatched_better_state,
                matching_state,
            ]
        )
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
                "binding_source": "snapshot:browser_snapshot",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id="req-browser-binding-compatible",
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.status == "resolved"
    assert result.metadata["record_source"]["request_id"] == "req-browser-binding-compatible"
    assert result.metadata["resolved_context"]["tab_id"] == "tab-1"
    assert result.metadata["resolved_context"]["element_ref"] == "snapshot:browser_snapshot#node:1"


def test_yue_action_state_browser_continuity_lookup_backend_blocks_when_binding_source_is_ambiguous():
    candidate_a = SimpleNamespace(
        id=3,
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-a",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                },
            },
        },
    )
    candidate_b = SimpleNamespace(
        id=2,
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-b",
                    "element_ref": "snapshot:other_snapshot#node:2",
                    "binding_source": "snapshot:other_snapshot",
                },
            },
        },
    )
    backend = YueActionStateBrowserContinuityLookupBackend(
        chat_service=SimpleNamespace(
            list_action_states_by_request_id=lambda *args, **kwargs: [candidate_a, candidate_b]
        )
    )
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        mapped_tool="builtin:browser_click",
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "validated_arguments": {
                "session_id": "session-1",
            },
        },
    )

    result = backend.lookup(
        RuntimeBrowserContinuityLookupRequest(
            invocation_request=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={},
                enabled_tools=["builtin:browser_click"],
            ),
            invocation_result=invocation,
            request_id="req-browser-ambiguous",
            browser_continuity={"contract_mode": "authoritative_target_mutation"},
            browser_continuity_resolution={"resolution_mode": "session_tab_target_lookup"},
            provided_context={"session_id": "session-1"},
            missing_context=["tab_id", "element_ref"],
        )
    )

    assert result.status == "blocked"
    assert result.resolved is False
    assert result.metadata["reason"] == "binding_source_ambiguous"
    assert result.metadata["candidate_binding_sources"] == [
        "snapshot:browser_snapshot",
        "snapshot:other_snapshot",
    ]


def test_skill_action_execution_service_preflight_resolves_browser_continuity_from_action_state_lookup():
    invocation = RuntimeSkillActionInvocationResult(
        accepted=False,
        skill_name="browser-operator",
        skill_version="1.0.0",
        action_id="click_element",
        approval_required=True,
        approval_policy="manual",
        mapped_tool="builtin:browser_click",
        validation_errors=["browser_tab_required", "browser_target_required"],
        execution_mode="tool_only",
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["binding_source"],
                "optional": ["session_id", "tab_id"],
            },
            "validated_arguments": {
                "session_id": "session-1",
                "binding_source": "snapshot:browser_snapshot",
            },
            "browser_continuity": {
                "contract_mode": "authoritative_target_mutation",
                "current_execution_mode": "resumable_session_required",
                "authoritative_target_required": True,
                "resumable_continuity": "deferred",
            },
            "browser_continuity_resolution": {
                "resolver_contract_version": 1,
                "resolution_mode": "session_tab_target_lookup",
                "continuity_status": "resolver_deferred",
                "session_lookup_required": True,
                "tab_lookup_required": True,
                "target_lookup_required": True,
                "provided_context": {
                    "has_url": False,
                    "has_session_id": True,
                    "has_tab_id": False,
                    "has_element_ref": False,
                },
                "missing_context": ["tab_id", "element_ref"],
                "contract_mode": "authoritative_target_mutation",
            },
        },
    )
    persisted_state = SimpleNamespace(
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        payload={
            "metadata": {
                "validated_arguments": {
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                    "binding_source": "snapshot:browser_snapshot",
                },
                "browser_continuity_resolution": {
                    "continuity_status": "resolved",
                    "resolved_context": {
                        "resolved_context_id": "browser_ctx:prior",
                        "session_id": "session-1",
                        "tab_id": "tab-1",
                        "element_ref": "snapshot:browser_snapshot#node:1",
                        "resolution_mode": "explicit_request_context",
                        "resolution_source": "explicit_request_context",
                        "resolved_target_kind": "authoritative_target",
                    },
                },
            },
        },
    )
    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )(),
        continuity_resolver=ExplicitContextBrowserContinuityResolver(
            lookup_backend=YueActionStateBrowserContinuityLookupBackend(
                chat_service=SimpleNamespace(
                    list_action_states_by_request_id=lambda *args, **kwargs: [persisted_state]
                )
            )
        ),
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser-resume",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={"session_id": "session-1", "binding_source": "snapshot:browser_snapshot"},
                enabled_tools=["builtin:browser_click"],
            ),
        )
    )

    assert result.metadata["browser_continuity_resolver"] == {
        "resolver_id": "explicit_context",
        "status": "resolved",
        "resolved": True,
    }
    assert result.metadata["browser_continuity_resolution"]["resolution_mode"] == "action_state_lookup"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["tab_id"] == "tab-1"
    assert result.metadata["browser_continuity_resolution"]["resolved_context"]["element_ref"] == "snapshot:browser_snapshot#node:1"
    assert result.metadata["browser_continuity_resolution"]["lookup_backend"] == {
        "backend_id": "yue_action_state",
        "status": "resolved",
        "resolved": True,
    }

def test_skill_action_execution_service_preflight_returns_ready_for_browser_open_auto_policy():
    action = RuntimeSkillActionDescriptor(
        id="open_page",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_open",
        approval_policy="auto",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "tab_id": {"type": "string"},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "open",
            "runtime_metadata_expectations": {
                "required": ["operation", "url"],
                "optional": ["tab_id"],
            },
        },
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_open"],
        arguments={"url": "https://example.com", "tab_id": "tab-1"},
    )
    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )()
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser-open",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="open_page",
                arguments={"url": "https://example.com", "tab_id": "tab-1"},
                enabled_tools=["builtin:browser_open"],
            )
        )
    )

    stub_results = service.build_stub_execution_results(preflight_result=result)

    assert result.status == "ready"
    assert result.lifecycle_status == "preflight_ready"
    assert result.metadata["operation"] == "open"
    assert result.metadata["runtime_metadata"]["url"] == "https://example.com"
    assert [item.lifecycle_status for item in stub_results] == ["queued", "skipped"]

def test_skill_action_execution_service_preflight_ready_browser_event_carries_resolved_continuity_metadata():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        approval_policy="manual",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": ["session_id", "tab_id", "binding_source", "binding_session_id", "binding_tab_id"],
            },
        },
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={
            "session_id": "session-1",
            "tab_id": "tab-1",
            "binding_source": "snapshot:browser_snapshot",
            "binding_session_id": "session-1",
            "binding_tab_id": "tab-1",
            "element_ref": "snapshot:browser_snapshot#node:1",
        },
    )
    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )()
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser-ready",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={
                    "session_id": "session-1",
                    "tab_id": "tab-1",
                    "binding_source": "snapshot:browser_snapshot",
                    "binding_session_id": "session-1",
                    "binding_tab_id": "tab-1",
                    "element_ref": "snapshot:browser_snapshot#node:1",
                },
                enabled_tools=["builtin:browser_click"],
            )
        )
    )

    payload = result.event_payloads[1]
    assert payload["status"] == "approval_required"
    assert payload["lifecycle_status"] == "preflight_approval_required"
    assert payload["metadata"]["browser_continuity_resolution"]["continuity_status"] == "resolved"
    assert payload["metadata"]["browser_continuity_resolution"]["resolution_mode"] == "explicit_request_context"
    assert payload["metadata"]["browser_continuity_resolution"]["resolved_context"]["session_id"] == "session-1"
    assert payload["metadata"]["browser_continuity_resolution"]["resolved_context"]["tab_id"] == "tab-1"
    assert payload["metadata"]["browser_continuity_resolver"] == {
        "resolver_id": "explicit_context",
        "status": "resolved",
        "resolved": True,
    }

def test_skill_registry_validate_action_invocation_handles_missing_action():
    registry = SkillRegistry()

    result = registry.validate_action_invocation(
        RuntimeSkillActionInvocationRequest(
            skill_name="missing-skill",
            skill_version="1.0.0",
            action_id="generate",
            enabled_tools=["builtin:docs_read"],
        )
    )

    assert result.accepted is False
    assert result.validation_errors == ["Action descriptor not found"]

def test_build_action_invocation_event_payload():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])

    payload = build_action_invocation_event(phase="preflight", result=invocation, request_id="req-1")

    assert payload["event"] == "skill.action.preflight"
    assert payload["skill_name"] == "action-skill"
    assert payload["action_id"] == "generate"
    assert payload["request_id"] == "req-1"
    assert payload["invocation_id"] is None

def test_build_action_execution_result_event_payload():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])

    payload = build_action_execution_result_event(status="approval_required", result=invocation, request_id="req-1")

    assert payload["event"] == "skill.action.result"
    assert payload["status"] == "approval_required"
    assert payload["lifecycle_phase"] == "preflight"
    assert payload["lifecycle_status"] == "preflight_approval_required"
    assert payload["skill_name"] == "action-skill"
    assert payload["action_id"] == "generate"
    assert payload["invocation_id"] is None

def test_build_action_execution_result_event_includes_metadata_payload():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
    )

    payload = build_action_execution_result_event(
        status="blocked",
        result=invocation,
        request_id="req-browser",
        metadata={
            "browser_continuity_resolution": {
                "resolution_mode": "explicit_request_context",
                "continuity_status": "resolved",
            },
            "browser_continuity_resolver": {
                "resolver_id": "explicit_context",
                "status": "resolved",
                "resolved": True,
            },
        },
    )

    assert payload["metadata"]["browser_continuity_resolution"]["resolution_mode"] == "explicit_request_context"
    assert payload["metadata"]["browser_continuity_resolver"]["resolver_id"] == "explicit_context"

def test_skill_action_execution_service_preflight_returns_approval_required():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
      safety: workspace_write
actions:
  - id: generate
    tool: builtin:docs_read
    resource: generate
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()
        service = SkillActionExecutionService(registry)

        result = service.preflight(
            RuntimeSkillActionExecutionRequest(
                request_id="req-approval",
                invocation=RuntimeSkillActionInvocationRequest(
                    skill_name="action-skill",
                    skill_version="1.0.0",
                    action_id="generate",
                    enabled_tools=["builtin:docs_read"],
                ),
            )
        )

        assert result.status == "approval_required"
        assert result.lifecycle_phase == "preflight"
        assert result.lifecycle_status == "preflight_approval_required"
        assert result.execution_mode == "non_executing"
        assert result.request_id == "req-approval"
        assert len(result.event_payloads) == 2
        assert result.event_payloads[0]["event"] == "skill.action.preflight"
        assert result.event_payloads[0]["lifecycle_status"] == "preflight_evaluated"
        assert result.event_payloads[1]["event"] == "skill.action.result"
        assert result.event_payloads[1]["status"] == "approval_required"
        assert result.event_payloads[1]["lifecycle_status"] == "preflight_approval_required"

def test_skill_action_execution_service_preflight_returns_blocked_for_missing_tool():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_dir = os.path.join(tmp_dir, "action-skill")
        os.makedirs(os.path.join(pkg_dir, "scripts"), exist_ok=True)
        with open(os.path.join(pkg_dir, "SKILL.md"), "w") as f:
            f.write("""---
name: action-skill
version: 1.0.0
description: action skill
capabilities: ["pkg"]
entrypoint: system_prompt
---
## System Prompt
Action prompt.
""")
        with open(os.path.join(pkg_dir, "manifest.yaml"), "w") as f:
            f.write("""format_version: 1
name: action-skill
version: 1.0.0
description: action skill
entrypoint: system_prompt
capabilities: ["pkg"]
resources:
  scripts:
    - id: generate
      path: scripts/generate.py
      runtime: python
actions:
  - id: generate
    tool: builtin:docs_read
    resource: generate
    approval_policy: manual
""")
        with open(os.path.join(pkg_dir, "scripts", "generate.py"), "w") as f:
            f.write("print('generate')")

        registry = SkillRegistry(skill_dirs=[tmp_dir])
        registry.load_all()
        service = SkillActionExecutionService(registry)

        result = service.preflight(
            RuntimeSkillActionExecutionRequest(
                request_id="req-blocked",
                invocation=RuntimeSkillActionInvocationRequest(
                    skill_name="action-skill",
                    skill_version="1.0.0",
                    action_id="generate",
                    enabled_tools=["builtin:docs_search"],
                ),
            )
        )

        assert result.status == "blocked"
        assert result.lifecycle_status == "preflight_blocked"
        assert result.invocation.missing_requirements == ["tool:builtin:docs_read"]
        assert result.event_payloads[1]["status"] == "blocked"
        assert result.event_payloads[1]["lifecycle_status"] == "preflight_blocked"

def test_skill_action_execution_service_preflight_returns_blocked_for_missing_action():
    registry = SkillRegistry()
    service = SkillActionExecutionService(registry)

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-missing",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="missing-skill",
                skill_version="1.0.0",
                action_id="generate",
                enabled_tools=["builtin:docs_read"],
            ),
        )
    )

    assert result.status == "blocked"
    assert result.lifecycle_status == "preflight_blocked"
    assert result.invocation.validation_errors == ["Action descriptor not found"]
    assert result.event_payloads[1]["status"] == "blocked"
    assert result.event_payloads[1]["lifecycle_status"] == "preflight_blocked"

def test_skill_action_execution_service_preflight_blocked_browser_event_carries_continuity_metadata():
    action = RuntimeSkillActionDescriptor(
        id="click_element",
        name="browser-operator",
        version="1.0.0",
        tool="builtin:browser_click",
        safety="browser_write",
        approval_policy="manual",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tab_id": {"type": "string"},
                "binding_source": {"type": "string"},
                "binding_session_id": {"type": "string"},
                "binding_tab_id": {"type": "string"},
                "element_ref": {"type": "string"},
            },
            "required": ["element_ref"],
            "additionalProperties": False,
        },
        metadata={
            "tool_family": "agent_browser",
            "operation": "click",
            "runtime_metadata_expectations": {
                "required": ["operation", "element_ref"],
                "optional": ["session_id", "tab_id", "binding_source", "binding_session_id", "binding_tab_id"],
            },
        },
    )
    invocation = SkillPolicyGate.validate_action_invocation(
        action,
        enabled_tools=["builtin:browser_click"],
        arguments={"element_ref": "button:submit"},
    )
    service = SkillActionExecutionService(
        type(
            "StubRegistry",
            (),
            {"validate_action_invocation": lambda self, request: invocation},
        )()
    )

    result = service.preflight(
        RuntimeSkillActionExecutionRequest(
            request_id="req-browser-blocked",
            invocation=RuntimeSkillActionInvocationRequest(
                skill_name="browser-operator",
                skill_version="1.0.0",
                action_id="click_element",
                arguments={"element_ref": "button:submit"},
                enabled_tools=["builtin:browser_click"],
            )
        )
    )

    payload = result.event_payloads[1]
    assert payload["status"] == "blocked"
    assert payload["lifecycle_status"] == "preflight_blocked"
    assert payload["metadata"]["browser_continuity_resolution"]["continuity_status"] == "blocked"
    assert payload["metadata"]["browser_continuity_resolution"]["missing_context"] == ["session_id", "tab_id"]
    assert payload["metadata"]["browser_continuity_resolver"] == {
        "resolver_id": "explicit_context",
        "status": "blocked",
        "resolved": False,
    }

def test_build_action_execution_transition_event_payload():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])

    payload = build_action_execution_transition_event(
        status="queued",
        result=invocation,
        request_id="req-queued",
        lifecycle_phase="execution",
        metadata={"queue": "default"},
    )

    assert payload["event"] == "skill.action.result"
    assert payload["status"] == "queued"
    assert payload["lifecycle_phase"] == "execution"
    assert payload["lifecycle_status"] == "queued"
    assert payload["metadata"] == {"queue": "default"}

def test_skill_action_execution_service_build_transition_result_for_running_state():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])
    service = SkillActionExecutionService(SkillRegistry())

    result = service.build_transition_result(
        invocation=invocation,
        status="running",
        request_id="req-running",
        lifecycle_phase="execution",
        metadata={"attempt": 1},
    )

    assert result.status == "running"
    assert result.lifecycle_phase == "execution"
    assert result.lifecycle_status == "running"
    assert result.request_id == "req-running"
    assert result.metadata["attempt"] == 1
    assert "invocation_id" in result.metadata
    assert len(result.event_payloads) == 1
    assert result.event_payloads[0]["event"] == "skill.action.result"
    assert result.event_payloads[0]["lifecycle_phase"] == "execution"
    assert result.event_payloads[0]["lifecycle_status"] == "running"
    assert result.event_payloads[0]["metadata"]["attempt"] == 1
    assert "invocation_id" in result.event_payloads[0]["metadata"]

def test_skill_action_execution_service_builds_stub_execution_results_for_ready_preflight():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])
    service = SkillActionExecutionService(SkillRegistry())
    preflight_result = service.build_transition_result(
        invocation=invocation,
        status="ready",
        request_id="req-ready",
        lifecycle_phase="preflight",
        lifecycle_status="preflight_ready",
        metadata={"provider": "openai"},
    )

    results = service.build_stub_execution_results(preflight_result=preflight_result)

    assert [item.lifecycle_status for item in results] == ["queued", "skipped"]
    assert results[0].event_payloads[0]["metadata"]["reason"] == "non_executing_by_design"
    assert results[1].event_payloads[0]["lifecycle_phase"] == "execution"

def test_skill_action_execution_service_builds_stub_execution_results_for_approval_preflight():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])
    service = SkillActionExecutionService(SkillRegistry())
    preflight_result = service.build_transition_result(
        invocation=invocation,
        status="approval_required",
        request_id="req-approval",
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        metadata={"provider": "openai"},
    )

    results = service.build_stub_execution_results(preflight_result=preflight_result)

    assert len(results) == 1
    assert results[0].status == "awaiting_approval"
    assert results[0].lifecycle_status == "awaiting_approval"
    assert results[0].metadata["reason"] == "approval_required"
    assert "approval_token" in results[0].metadata

def test_build_action_execution_stub_message_for_awaiting_approval():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])
    service = SkillActionExecutionService(SkillRegistry())
    result = service.build_transition_result(
        invocation=invocation,
        status="awaiting_approval",
        request_id="req-skip",
        lifecycle_phase="execution",
        lifecycle_status="awaiting_approval",
        metadata={"reason": "approval_required"},
    )

    message = build_action_execution_stub_message(result)

    assert "is awaiting approval before any platform-tool continuation can be considered" in message

def test_skill_action_execution_service_builds_approval_result_and_resumes_execution():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])
    service = SkillActionExecutionService(SkillRegistry())
    preflight_result = service.build_transition_result(
        invocation=invocation,
        status="approval_required",
        request_id="req-approval",
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
        metadata={"provider": "openai"},
    )
    approval_result = service.build_approval_result(
        preflight_result=preflight_result,
        approval_request=RuntimeSkillActionApprovalRequest(
            skill_name="action-skill",
            skill_version="1.0.0",
            action_id="generate",
            approved=True,
            approval_token="approval:action-skill:1.0.0:generate:req-approval",
            request_id="req-approval",
        ),
    )

    resumed_results = service.build_stub_execution_results(
        preflight_result=preflight_result,
        approval_result=approval_result,
    )

    assert approval_result.approved is True
    assert approval_result.lifecycle_status == "approved"
    assert approval_result.approval_token == "approval:action-skill:1.0.0:generate:req-approval"
    assert build_action_approval_message(approval_result) == "[Action Approval] `action-skill.generate` was approved. Platform-tool action flow can continue."
    assert [item.lifecycle_status for item in resumed_results] == ["queued", "skipped"]
    assert resumed_results[0].metadata["reason"] == "approved_resume"

def test_skill_action_execution_service_rejects_invalid_approval_token():
    action = RuntimeSkillActionDescriptor(
        id="generate",
        name="action-skill",
        version="1.0.0",
        tool="builtin:docs_read",
        approval_policy="manual",
    )
    invocation = SkillPolicyGate.validate_action_invocation(action, enabled_tools=["builtin:docs_read"])
    service = SkillActionExecutionService(SkillRegistry())
    preflight_result = service.build_transition_result(
        invocation=invocation,
        status="approval_required",
        request_id="req-approval",
        lifecycle_phase="preflight",
        lifecycle_status="preflight_approval_required",
    )

    approval_result = service.build_approval_result(
        preflight_result=preflight_result,
        approval_request=RuntimeSkillActionApprovalRequest(
            skill_name="action-skill",
            skill_version="1.0.0",
            action_id="generate",
            approved=True,
            approval_token="bad-token",
        ),
    )

    assert approval_result.approved is False
    assert approval_result.lifecycle_status == "invalid"
    assert approval_result.metadata["reason"] == "approval_token_mismatch"

if __name__ == "__main__":
    pytest.main([__file__])
