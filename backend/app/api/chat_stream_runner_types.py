from dataclasses import dataclass
from typing import Any, List


@dataclass
class PromptRuntimeDeps:
    skill_registry: Any
    skill_action_execution_service: Any
    markdown_skill_adapter: Any
    skill_policy_gate: Any
    assemble_runtime_prompt: Any
    build_scope_summary_block: Any
    emit_skill_effectiveness_event: Any
    resolve_skill_runtime_state: Any
    action_preflight_message_builder: Any
    action_approval_message_builder: Any
    action_execution_message_builder: Any


@dataclass
class RetryRuntimeDeps:
    resolve_retry_targets: Any
    build_tool_call_retry_event: Any
    build_tool_call_retry_success_event: Any
    build_tool_call_retry_failed_event: Any
    build_tool_call_mismatch_event: Any
    build_tool_call_mismatch_message: Any


@dataclass
class StreamRunnerDeps:
    logger: Any
    agent_store: Any
    tool_registry: Any
    fetch_ollama_models: Any
    get_model: Any
    chat_service: Any
    config_service: Any
    build_system_prompt: Any
    get_parser: Any
    calculate_usage: Any
    handle_llm_exception: Any
    prompt: PromptRuntimeDeps
    retry: RetryRuntimeDeps
    collect_tool_names: Any
    patch_model_settings: Any
    build_agent_deps: Any
    ensure_ollama_model_available: Any
    format_citations_suffix: Any
    append_continue_message_if_needed: Any
    append_citation_suffix_if_needed: Any
    persist_assistant_message: Any
    should_handle_tool_call_mismatch: Any
    tool_event_tracker_cls: Any
    normalize_finished_ts: Any
    serialize_sse_payload: Any
    iso_utc_now: Any
    resolve_reasoning_state: Any
    build_runtime_meta_payload: Any
    run_agent_stream: Any
    refine_title_once_fn: Any
    build_chat_response_log_payload: Any
    safe_json_log: Any
    env_flag: Any
    env_flag_with_fallback: Any
    agent_cls: Any
    usage_limits_cls: Any


@dataclass
class PreparedRuntime:
    emitter: Any
    tool_tracker: Any
    tools: List[Any]
    model: Any
    multimodal_service: Any
    validated_images: List[str]
    request: Any
    model_capabilities: Any
    vision_enabled: bool
    authorized_tools: List[str]


@dataclass
class PromptPreparation:
    final_tools_list: List[str]
    selected_skill_spec: Any
    selection_reason_code: str
    selection_source: str
    selection_score: int
    visible_skill_count: int
    available_skill_count: int
    always_injected_count: int
    selected_group_ids: List[str]
    resolved_skill_count: int
    summary_injected: bool
    scope_summary_injected: bool
    effective_scope_count: int
