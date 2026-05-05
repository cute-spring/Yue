from app.services.jira.action_preview import extract_jira_action_preview, resolve_repo_jira_skill_runtime


def test_extract_jira_action_preview_reads_json_fence() -> None:
    response = """
Drafted the issue update below.

```jira-action-preview
{"action":"add_comment","args":{"issue_key":"YUE-123","comment":"Blocked on API review."},"reason":"Keep the issue activity log current."}
```
"""

    preview = extract_jira_action_preview(response)

    assert preview is not None
    assert preview.action_id == "add_comment"
    assert preview.arguments == {
        "issue_key": "YUE-123",
        "comment": "Blocked on API review.",
    }
    assert preview.reason == "Keep the issue activity log current."


def test_extract_jira_action_preview_returns_none_for_invalid_shape() -> None:
    response = """
```jira-action-preview
{"action":"add_comment"}
```
"""

    assert extract_jira_action_preview(response) is None


def test_resolve_repo_jira_skill_runtime_loads_repo_manifest() -> None:
    skill, action_service = resolve_repo_jira_skill_runtime("jira:1.0.0")

    assert skill is not None
    assert skill.name == "jira"
    assert action_service is not None
