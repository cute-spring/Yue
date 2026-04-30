from app.mcp.builtin.exec import ExecTool, ExecToolConfig


def test_exec_tool_description_mentions_general_use_and_document_discovery():
    tool = ExecTool(
        ExecToolConfig(
            timeout_s=60,
            working_dir=None,
            deny_patterns=[],
            allow_patterns=[],
            restrict_to_workspace=False,
            path_append="",
            max_output_chars=1000,
            max_concurrency=None,
            enable_windows_path_checks=False,
            log_rejections=False,
        )
    )

    assert "general-purpose shell tool" in tool.description
    assert "not limited to document search" in tool.description
    assert "ls, find" in tool.description
