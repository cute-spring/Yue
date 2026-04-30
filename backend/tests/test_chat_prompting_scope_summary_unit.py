import os
from types import SimpleNamespace
from unittest.mock import patch

from app.services import chat_prompting
from app.services import doc_retrieval


def test_build_scope_summary_uses_allow_roots_only_and_not_deny_or_agent_doc_roots():
    agent = SimpleNamespace(
        enabled_tools=["builtin:docs_read"],
        doc_roots=["/agent/legacy-root"],
    )
    config_service = SimpleNamespace(
        get_doc_access=lambda: {
            "allow_roots": ["/workspace/docs", "/workspace/notes"],
            "deny_roots": ["/workspace/docs/private"],
        }
    )

    with patch.dict(
        os.environ,
        {
            "PROMPT_SCOPE_SUMMARY_ENABLED": "true",
            "PROMPT_SCOPE_SUMMARY_REVEAL_PATHS": "true",
            "PROMPT_SCOPE_SUMMARY_MAX_ROOTS": "10",
        },
        clear=False,
    ):
        block, count = chat_prompting.build_scope_summary_block(
            agent,
            config_service=config_service,
            doc_retrieval=doc_retrieval,
        )

    assert count == 2
    assert "### Scope Summary" in (block or "")
    assert "/workspace/docs" in (block or "")
    assert "/workspace/notes" in (block or "")
    assert "/workspace/docs/private" not in (block or "")
    assert "/agent/legacy-root" not in (block or "")
    assert "### Document Discovery Hints" in (block or "")
    assert ".xlsx" in (block or "")
    assert "not limited to search-only usage" in (block or "")
    assert "system-ops-expert" in (block or "")


def test_build_scope_summary_applies_to_excel_and_exec_capabilities_too():
    config_service = SimpleNamespace(
        get_doc_access=lambda: {
            "allow_roots": ["/workspace/docs"],
            "deny_roots": [],
        }
    )

    with patch.dict(
        os.environ,
        {
            "PROMPT_SCOPE_SUMMARY_ENABLED": "true",
            "PROMPT_SCOPE_SUMMARY_REVEAL_PATHS": "true",
        },
        clear=False,
    ):
        excel_block, excel_count = chat_prompting.build_scope_summary_block(
            SimpleNamespace(enabled_tools=["builtin:excel_read"], doc_roots=[]),
            config_service=config_service,
            doc_retrieval=doc_retrieval,
        )
        exec_block, exec_count = chat_prompting.build_scope_summary_block(
            SimpleNamespace(enabled_tools=["builtin:exec"], doc_roots=[]),
            config_service=config_service,
            doc_retrieval=doc_retrieval,
        )

    assert excel_count == 1
    assert exec_count == 1
    assert "Document Discovery Hints" in (excel_block or "")
    assert "Document Discovery Hints" in (exec_block or "")


def test_build_scope_summary_reveals_full_paths_by_default():
    agent = SimpleNamespace(
        enabled_tools=["builtin:exec"],
        doc_roots=[],
    )
    config_service = SimpleNamespace(
        get_doc_access=lambda: {
            "allow_roots": ["/Users/gavinzhang/Desktop/test_files"],
            "deny_roots": [],
        }
    )

    with patch.dict(
        os.environ,
        {
            "PROMPT_SCOPE_SUMMARY_ENABLED": "true",
        },
        clear=False,
    ):
        os.environ.pop("PROMPT_SCOPE_SUMMARY_REVEAL_PATHS", None)
        block, count = chat_prompting.build_scope_summary_block(
            agent,
            config_service=config_service,
            doc_retrieval=doc_retrieval,
        )

    assert count == 1
    assert "/Users/gavinzhang/Desktop/test_files" in (block or "")
    assert "./Desktop/test_files" not in (block or "")
    assert "Use exact absolute root paths above" in (block or "")


def test_assemble_runtime_prompt_does_not_inject_agent_doc_roots_legacy_block():
    agent = SimpleNamespace(
        name="Normal Agent",
        system_prompt="You are helpful.",
        provider="openai",
        model="gpt-4o",
        enabled_tools=["builtin:docs_read"],
        doc_roots=["/agent/legacy-root"],
    )

    result = chat_prompting.assemble_runtime_prompt(
        agent_config=agent,
        request_system_prompt=None,
        request_message="read docs",
        provider=None,
        model_name=None,
        selected_skill_spec=None,
        always_skill_specs=[],
        summary_block=None,
        feature_flags={"skill_runtime_enabled": True},
        skill_registry=SimpleNamespace(get_full_skill=lambda *_args, **_kwargs: None),
        markdown_skill_adapter=SimpleNamespace(to_descriptor=lambda *_args, **_kwargs: None),
        skill_policy_gate=SimpleNamespace(check_tool_intersection=lambda *_args, **_kwargs: []),
        build_scope_summary_block=lambda _agent: ("### Scope Summary\n- /workspace/docs", 1),
        runtime_seams=None,
    )

    assert "### Scope Summary" in result.system_prompt
    assert "可检索目录" not in result.system_prompt
    assert "/agent/legacy-root" not in result.system_prompt
