from app.services.skills.compatibility import SkillCompatibilityEvaluator
from app.services.skills.models import SkillActionSpec, SkillPackageSpec


def test_compatibility_evaluator_rejects_unknown_tool_by_default_supported_set():
    package = SkillPackageSpec(
        name="tool-guard-skill",
        version="1.0.0",
        description="tool guard",
        capabilities=["analysis"],
        entrypoint="system_prompt",
        actions=[
            SkillActionSpec(
                id="a1",
                tool="builtin:not_registered_tool",
                path="scripts/a1.py",
            )
        ],
    )
    evaluator = SkillCompatibilityEvaluator()

    result = evaluator.evaluate_package(package)

    assert result.status == "incompatible"
    assert "builtin:not_registered_tool" in result.unsupported_tools
    assert any("Unsupported tool required" in issue for issue in result.issues)
