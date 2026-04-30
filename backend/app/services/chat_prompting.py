import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic_ai.messages import ImageUrl, ModelRequest, ModelResponse, TextPart, UserPromptPart


EST_CHARS_PER_TOKEN = 3
MAX_CONTEXT_TOKENS = 100000
MAX_SINGLE_MSG_TOKENS = 20000


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // EST_CHARS_PER_TOKEN


def env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def safe_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def env_flag_with_fallback(primary: str, legacy: str, default: bool) -> bool:
    raw_primary = os.getenv(primary)
    if raw_primary is not None:
        return raw_primary.strip().lower() in {"1", "true", "yes", "on"}
    return env_flag(legacy, default)


def safe_int_env_with_fallback(primary: str, legacy: str, default: int) -> int:
    raw_primary = os.getenv(primary)
    if raw_primary is not None:
        try:
            value = int(raw_primary)
        except Exception:
            return default
        return value if value > 0 else default
    return safe_int_env(legacy, default)


DISCOVERY_EXTENSIONS = [".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".xltx", ".xltm", ".csv", ".md", ".txt"]


def has_document_discovery_capability(agent_config: Any) -> bool:
    tools = getattr(agent_config, "enabled_tools", []) or []
    for tool in tools:
        if not isinstance(tool, str):
            continue
        if "docs_" in tool or "excel_" in tool or tool in {"builtin:exec", "exec"}:
            return True
    return False


def mask_scope_root(path: str, *, doc_retrieval: Any) -> str:
    if not path:
        return path
    project_root = doc_retrieval.get_project_root()
    path_real = os.path.realpath(path)
    project_real = os.path.realpath(project_root)
    try:
        if os.path.commonpath([project_real, path_real]) == project_real:
            rel = os.path.relpath(path_real, project_real).replace(os.sep, "/")
            return rel if rel != "." else "."
    except Exception:
        pass
    parts = [p for p in path_real.replace("\\", "/").split("/") if p]
    tail = "/".join(parts[-2:]) if len(parts) >= 2 else (parts[0] if parts else path_real)
    return f".../{tail}" if tail else path_real


def build_scope_summary_block(
    agent_config: Any,
    *,
    config_service: Any,
    doc_retrieval: Any,
) -> Tuple[Optional[str], int]:
    if not agent_config or not has_document_discovery_capability(agent_config):
        return None, 0
    if not env_flag("PROMPT_SCOPE_SUMMARY_ENABLED", True):
        return None, 0
    reveal_paths = env_flag("PROMPT_SCOPE_SUMMARY_REVEAL_PATHS", True)
    max_roots = safe_int_env("PROMPT_SCOPE_SUMMARY_MAX_ROOTS", 3)
    doc_roots = getattr(agent_config, "doc_roots", None) or []
    doc_access = config_service.get_doc_access()
    allow_roots = doc_access.get("allow_roots") or []
    deny_roots = doc_access.get("deny_roots") or []
    try:
        effective_roots = doc_retrieval.resolve_docs_roots_for_search(
            None,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )
    except Exception:
        effective_roots = []
    if not effective_roots:
        return None, 0
    shown = effective_roots[:max_roots]
    display_roots = shown if reveal_paths else [mask_scope_root(p, doc_retrieval=doc_retrieval) for p in shown]
    lines = ["### Scope Summary", f"- Effective roots: {len(effective_roots)}"]
    lines.extend(f"- {root}" for root in display_roots)
    if len(effective_roots) > len(shown):
        lines.append(f"- ... and {len(effective_roots) - len(shown)} more")
    lines.append("### Document Discovery Hints")
    lines.append("- For document filename/path/extension discovery, prefer OS-native search commands through exec or use docs_list first.")
    lines.append("- If the system-ops-expert skill is visible, prefer it first for document discovery workflows before file-specific readers such as excel_profile or docs_read.")
    lines.append("- Use exact absolute root paths above when building exec/docs/excel paths; avoid guessing with unrelated relative prefixes such as ./Desktop/...")
    lines.append(f"- Common document extensions: {', '.join(DISCOVERY_EXTENSIONS)}")
    lines.append("- Use exec for any efficient shell task when appropriate; document discovery is only one high-value use case.")
    lines.append("- For file-specific readers such as excel_read/excel_query/docs_read, locate a concrete file path before calling the tool.")
    lines.append("- Preferred roots above are guidance for document-oriented tasks; exec itself is not limited to search-only usage.")
    return "\n".join(lines), len(effective_roots)


def build_history_from_chat(
    existing_chat: Any,
    *,
    load_image_to_base64: Callable[[str], str],
    logger: Any,
) -> List[Any]:
    if not existing_chat:
        return []

    current_tokens = 0
    temp_history: List[Any] = []

    for message in reversed(existing_chat.messages):
        content = message.content or ""
        msg_tokens = estimate_tokens(content)

        if msg_tokens > MAX_SINGLE_MSG_TOKENS:
            keep_chars = MAX_SINGLE_MSG_TOKENS * EST_CHARS_PER_TOKEN
            content = content[:keep_chars] + "\n... (content truncated due to length)"
            msg_tokens = MAX_SINGLE_MSG_TOKENS

        if current_tokens + msg_tokens > MAX_CONTEXT_TOKENS:
            logger.info("Context limit reached. Dropping older messages. Current tokens: %s", current_tokens)
            break

        current_tokens += msg_tokens

        if message.role == "user":
            if message.images:
                parts = []
                content_text = (message.content or "").strip()
                if content_text:
                    parts.append(content_text)
                for img in message.images:
                    parts.append(ImageUrl(url=load_image_to_base64(img)))
                temp_history.append(ModelRequest(parts=[UserPromptPart(content=parts)]))
            else:
                temp_history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif message.role == "assistant":
            temp_history.append(ModelResponse(parts=[TextPart(content=content)]))

    return list(reversed(temp_history))


@dataclass
class SkillRuntimeState:
    selected_skill_spec: Any = None
    always_skill_specs: List[Any] = field(default_factory=list)
    selection_reason_code: str = "legacy_path"
    selection_source: str = "none"
    selection_score: int = 0
    visible_skill_count: int = 0
    available_skill_count: int = 0
    always_injected_count: int = 0
    selected_group_ids: List[str] = field(default_factory=list)
    resolved_skill_count: int = 0
    summary_block: Optional[str] = None


@dataclass
class PromptAssemblyResult:
    provider: Optional[str]
    model_name: Optional[str]
    system_prompt: str
    final_tools_list: List[str]
    selected_skill_spec: Any
    always_injected_count: int
    emitted_event: Optional[Dict[str, Any]] = None
    summary_injected: bool = False
    scope_summary_injected: bool = False
    effective_scope_count: int = 0


def resolve_skill_runtime_state(
    *,
    agent_config: Any,
    feature_flags: Dict[str, Any],
    chat_id: str,
    request_message: str,
    requested_skill: Optional[str],
    skill_router: Any,
    skill_registry: Any,
    chat_service: Any,
    skill_bind_min_score: int,
    skill_switch_delta: int,
    runtime_seams: Any = None,
) -> SkillRuntimeState:
    state = SkillRuntimeState()
    if not agent_config:
        return state

    state.selected_group_ids = list(getattr(agent_config, "skill_groups", None) or [])
    visibility_resolver = getattr(runtime_seams, "visibility_resolver", None) if runtime_seams else None
    if visibility_resolver is not None:
        resolved_refs = visibility_resolver.resolve_visible_skill_refs(agent_config)
    else:
        resolved_refs = skill_router.resolve_visible_skill_refs(agent_config)
    agent_config.resolved_visible_skills = resolved_refs
    state.resolved_skill_count = len(resolved_refs)

    if agent_config.skill_mode != "off":
        visible_skills = skill_router.get_visible_skills(agent_config)
        summary_lines = []
        for skill in visible_skills:
            status = "available" if skill.availability is not False else "unavailable"
            summary_lines.append(f"- {skill.name}: {skill.description} ({status})")
        if summary_lines:
            state.summary_block = "### Skill Summaries\n" + "\n".join(summary_lines)

    if not feature_flags.get("skill_runtime_enabled") or agent_config.skill_mode == "off":
        state.selection_reason_code = "skill_mode_off"
        chat_service.clear_session_skill(chat_id)
        return state

    bound_pair = chat_service.get_session_skill(chat_id)
    if isinstance(bound_pair, tuple) and len(bound_pair) >= 2:
        bound_name, bound_version = bound_pair[0], bound_pair[1]
    else:
        bound_name, bound_version = None, None
    bound_skill = skill_registry.get_skill(bound_name, bound_version) if bound_name else None

    visible_skills = skill_router.get_visible_skills(agent_config)
    state.visible_skill_count = len(visible_skills)
    state.available_skill_count = len([s for s in visible_skills if s.availability is not False])
    state.always_skill_specs = [s for s in visible_skills if s.always and s.availability is not False]

    if bound_skill and bound_skill not in visible_skills:
        bound_skill = None

    inferred_requested_skill = skill_router.infer_requested_skill(agent_config, request_message)

    if agent_config.skill_mode == "manual":
        explicit_requested_skill = requested_skill or inferred_requested_skill
        if explicit_requested_skill:
            state.selection_source = "explicit" if requested_skill else "inferred"
            state.selected_skill_spec, state.selection_score = skill_router.route_with_score(
                agent_config,
                request_message,
                requested_skill=explicit_requested_skill,
            )
        elif bound_skill:
            bound_score = skill_router.score_skill(bound_skill, request_message)
            if bound_score >= skill_bind_min_score:
                state.selected_skill_spec = bound_skill
                state.selection_score = bound_score
    elif agent_config.skill_mode == "auto":
        if inferred_requested_skill:
            state.selection_source = "inferred"
        best_skill, best_score = skill_router.route_with_score(
            agent_config,
            request_message,
            requested_skill=inferred_requested_skill,
        )
        if bound_skill:
            bound_score = skill_router.score_skill(bound_skill, request_message)
            if not best_skill:
                if bound_score >= skill_bind_min_score:
                    state.selected_skill_spec = bound_skill
                    state.selection_score = bound_score
            elif bound_skill.name == best_skill.name and bound_skill.version == best_skill.version:
                if best_score >= skill_bind_min_score:
                    state.selected_skill_spec = bound_skill
                    state.selection_score = best_score
            elif best_score >= max(bound_score + skill_switch_delta, skill_bind_min_score):
                state.selected_skill_spec = best_skill
                state.selection_score = best_score
            elif bound_score >= skill_bind_min_score:
                state.selected_skill_spec = bound_skill
                state.selection_score = bound_score
        elif best_skill and best_score >= skill_bind_min_score:
            state.selected_skill_spec = best_skill
            state.selection_score = best_score

    if state.selected_skill_spec:
        state.selection_reason_code = "skill_selected"
        chat_service.set_session_skill(chat_id, state.selected_skill_spec.name, state.selected_skill_spec.version)
    else:
        state.selection_reason_code = "no_matching_skill"
        chat_service.clear_session_skill(chat_id)

    return state


def build_always_skill_blocks(
    *,
    always_skill_specs: List[Any],
    selected_skill_spec: Any,
    provider: Optional[str],
    model_name: Optional[str],
    feature_flags: Dict[str, Any],
    skill_registry: Any,
    markdown_skill_adapter: Any,
) -> List[str]:
    blocks: List[str] = []
    for always_skill in always_skill_specs:
        if (
            selected_skill_spec
            and always_skill.name == selected_skill_spec.name
            and always_skill.version == selected_skill_spec.version
        ):
            continue
        resolved_always = skill_registry.get_full_skill(
            always_skill.name,
            always_skill.version,
            provider=provider,
            model_name=model_name,
        ) or always_skill
        always_descriptor = markdown_skill_adapter.to_descriptor(resolved_always)
        always_prompt = always_descriptor.prompt_blocks.get("system_prompt", "")
        always_instructions = always_descriptor.prompt_blocks.get("instructions", "")
        block = f"[Always Skill: {resolved_always.name}]\n{always_prompt}".strip()
        if always_instructions:
            block = f"{block}\n\n### Always Instructions\n{always_instructions}"
        blocks.append(block)
    return blocks


def assemble_runtime_prompt(
    *,
    agent_config: Any,
    request_system_prompt: Optional[str],
    request_message: str,
    provider: Optional[str],
    model_name: Optional[str],
    selected_skill_spec: Any,
    always_skill_specs: List[Any],
    summary_block: Optional[str],
    feature_flags: Dict[str, Any],
    skill_registry: Any,
    markdown_skill_adapter: Any,
    skill_policy_gate: Any,
    build_scope_summary_block: Callable[[Any], Tuple[Optional[str], int]],
    runtime_seams: Any = None,
) -> PromptAssemblyResult:
    system_prompt = request_system_prompt
    final_tools_list: List[str] = []
    emitted_event: Optional[Dict[str, Any]] = None
    always_injected_count = 0

    if selected_skill_spec:
        selected_skill_spec = skill_registry.get_full_skill(
            selected_skill_spec.name,
            selected_skill_spec.version,
            provider=provider or agent_config.provider,
            model_name=model_name or agent_config.model,
        ) or selected_skill_spec
        descriptor = markdown_skill_adapter.to_descriptor(selected_skill_spec)
        provider = provider or agent_config.provider
        model_name = model_name or agent_config.model

        persona = agent_config.system_prompt or ""
        skill_prompt = descriptor.prompt_blocks.get("system_prompt", "")
        instructions = descriptor.prompt_blocks.get("instructions", "")
        always_blocks = build_always_skill_blocks(
            always_skill_specs=always_skill_specs,
            selected_skill_spec=selected_skill_spec,
            provider=provider or agent_config.provider,
            model_name=model_name or agent_config.model,
            feature_flags=feature_flags,
            skill_registry=skill_registry,
            markdown_skill_adapter=markdown_skill_adapter,
        )
        always_injected_count = len(always_blocks)

        use_persona = not (agent_config.name == "Expert Mgr" or "Skill Expert Manager" in persona)
        prompt_injection_adapter = getattr(runtime_seams, "prompt_injection_adapter", None) if runtime_seams else None
        active_skill_block = f"[Active Skill: {selected_skill_spec.name}]\n{skill_prompt}"
        if prompt_injection_adapter is not None:
            system_prompt = prompt_injection_adapter.compose_prompt(
                base_prompt=persona if use_persona else "",
                skill_prompt=active_skill_block,
            )
        elif use_persona and persona:
            system_prompt = f"{persona}\n\n{active_skill_block}"
        else:
            system_prompt = active_skill_block
        if instructions:
            system_prompt += f"\n\n### Additional Instructions\n{instructions}"
        if always_blocks:
            system_prompt += "\n\n" + "\n\n".join(always_blocks)

        tool_capability_provider = getattr(runtime_seams, "tool_capability_provider", None) if runtime_seams else None
        if tool_capability_provider is not None:
            final_tools_list = tool_capability_provider.resolve_effective_tools(
                agent_tools=agent_config.enabled_tools,
                skill=selected_skill_spec,
            )
        else:
            allowed_tools = descriptor.tool_policy.get("allowed_tools")
            final_tools_list = skill_policy_gate.check_tool_intersection(agent_config.enabled_tools, allowed_tools)
        emitted_event = {"event": "skill_selected", "name": selected_skill_spec.name, "version": selected_skill_spec.version}
    elif agent_config:
        provider = provider or agent_config.provider
        model_name = model_name or agent_config.model
        system_prompt = system_prompt or agent_config.system_prompt
        if always_skill_specs:
            always_blocks = build_always_skill_blocks(
                always_skill_specs=always_skill_specs,
                selected_skill_spec=selected_skill_spec,
                provider=provider or agent_config.provider,
                model_name=model_name or agent_config.model,
                feature_flags=feature_flags,
                skill_registry=skill_registry,
                markdown_skill_adapter=markdown_skill_adapter,
            )
            if always_blocks:
                always_injected_count = len(always_blocks)
                system_prompt += "\n\n" + "\n\n".join(always_blocks)
        final_tools_list = agent_config.enabled_tools

    scope_summary_block, effective_scope_count = build_scope_summary_block(agent_config)
    scope_summary_injected = False
    if scope_summary_block and scope_summary_block not in (system_prompt or ""):
        system_prompt = (system_prompt or "").strip()
        if system_prompt:
            system_prompt += f"\n\n{scope_summary_block}"
        else:
            system_prompt = scope_summary_block
        scope_summary_injected = True

    if summary_block and not selected_skill_spec:
        system_prompt = system_prompt or ""
        if system_prompt:
            system_prompt = f"{system_prompt}\n\n{summary_block}"
        else:
            system_prompt = summary_block
    summary_injected = bool(summary_block and not selected_skill_spec)

    provider = provider or "openai"
    model_name = model_name or "gpt-4o"
    system_prompt = system_prompt or "You are a helpful assistant."

    return PromptAssemblyResult(
        provider=provider,
        model_name=model_name,
        system_prompt=system_prompt,
        final_tools_list=final_tools_list,
        selected_skill_spec=selected_skill_spec,
        always_injected_count=always_injected_count,
        emitted_event=emitted_event,
        summary_injected=summary_injected,
        scope_summary_injected=scope_summary_injected,
        effective_scope_count=effective_scope_count,
    )
