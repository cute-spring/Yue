import tempfile

from app.services.agent_store import AgentStore


def test_builtin_learning_coach_is_prompt_only_and_skill_constrained():
    with tempfile.TemporaryDirectory() as data_dir:
        store = AgentStore(data_dir=data_dir)
        learning_coach = store.get_agent("builtin-learning-coach")

    assert learning_coach is not None
    assert learning_coach.name == "Learning Coach"
    assert learning_coach.skill_mode == "manual"
    assert learning_coach.visible_skills == ["learning-coach:1.0.0"]
    assert learning_coach.enabled_tools == []
    assert learning_coach.require_citations is False
    assert "Learning Coach" in learning_coach.system_prompt
