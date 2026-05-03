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
    assert jira_agent.enabled_tools == [
        "jira_get_all_projects",
        "jira_search_fields",
        "jira_search",
        "jira_get_issue",
        "jira_get_transitions",
        "jira_get_agile_boards",
        "jira_get_board_issues",
        "jira_get_sprints_from_board",
        "jira_get_sprint_issues",
        "jira_get_link_types",
        "jira_write_actions",
    ]
    assert jira_agent.require_citations is True
    assert "Read operations are fully authorized by default" in jira_agent.system_prompt
    assert "jira-action-preview" in jira_agent.system_prompt
    assert "Sprint Health" in jira_agent.system_prompt
    assert jira_agent.model == "gpt-5.4"
