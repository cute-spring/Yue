import tempfile

from app.services.agent_store import AgentStore
from app.services.builtin_agent_catalog import BuiltinAgentCatalog


def test_builtin_jira_is_loaded_by_default_catalog():
    catalog = BuiltinAgentCatalog()

    agents = catalog.list_builtin_agents()
    by_id = {agent.id: agent for agent in agents}

    assert "builtin-jira" in by_id
    assert by_id["builtin-jira"].payload["name"] == "YUE Jira Project Assistant"


def test_builtin_jira_is_read_oriented_and_skill_constrained():
    with tempfile.TemporaryDirectory() as data_dir:
        store = AgentStore(data_dir=data_dir)
        jira_agent = store.get_agent("builtin-jira")

    assert jira_agent is not None
    assert jira_agent.skill_mode == "manual"
    assert jira_agent.visible_skills == ["jira:1.0.0"]
    assert jira_agent.enabled_tools == []
    assert jira_agent.require_citations is True
    assert "Do not perform Jira write actions" in jira_agent.system_prompt
    assert "ticket-draft workflows" in jira_agent.system_prompt
