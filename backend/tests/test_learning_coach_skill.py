from pathlib import Path

from app.services.skills.registry import SkillRegistry


def test_learning_coach_skill_loads_from_builtin_skill_directory():
    builtin_skills_dir = Path(__file__).resolve().parents[1] / "data" / "skills"
    registry = SkillRegistry(skill_dirs=[str(builtin_skills_dir)])
    registry.load_all()

    skill = registry.get_full_skill("learning-coach", "1.0.0")

    assert skill is not None
    assert skill.name == "learning-coach"
    assert skill.version == "1.0.0"
    assert "Socratic" in skill.system_prompt
    assert "L0" in skill.system_prompt
    assert "L6" in skill.system_prompt
