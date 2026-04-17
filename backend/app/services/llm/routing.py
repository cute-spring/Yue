from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Optional
from pydantic import BaseModel


class ResolutionSource(str, Enum):
    REQUEST_OVERRIDE = "request_override"
    AGENT_TIER = "agent_tier"
    AGENT_ROLE = "agent_role"
    SYSTEM_ROLE = "system_role"
    AUTO_UPGRADE = "auto_upgrade"
    LEGACY_AGENT_MODEL = "legacy_agent_model"
    LEGACY_GLOBAL_DEFAULT = "legacy_global_default"


class ResolvedModel(BaseModel):
    provider: str
    model: str
    role: Optional[str] = None
    tier: Optional[str] = None
    resolution_source: ResolutionSource
    fallback_used: bool = False
    upgrade_trigger: Optional[str] = None


class RoutingContext(BaseModel):
    request_provider: Optional[str] = None
    request_model: Optional[str] = None
    request_model_role: Optional[str] = None
    agent_provider: Optional[str] = None
    agent_model: Optional[str] = None
    agent_model_selection_mode: str = "direct"
    agent_model_tier: Optional[str] = None
    agent_model_role: Optional[str] = None
    agent_model_policy: str = "prefer_role"
    routing_default_mode: str = "legacy"
    routing_fallback_policy: str = "use_legacy_agent_model"
    auto_upgrade_enabled: bool = True
    tool_call_requires_role: str = "tool_use"
    multi_skill_requires_role: str = "reasoning"
    upgrade_on_tools: bool = True
    upgrade_on_multi_skill: bool = True
    has_tools: bool = False
    selected_tool_count: int = 0
    skill_count: int = 0
    has_images: bool = False
    task_hints: list[str] = []


def _clean_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_role_name(value: Any) -> Optional[str]:
    role = _clean_text(value)
    return role.lower() if role else None


def resolve_role_config(routing_config: dict[str, Any], role_name: str) -> Optional[dict[str, str]]:
    if not isinstance(routing_config, dict):
        return None

    roles = routing_config.get("roles")
    if not isinstance(roles, dict):
        return None

    target = _clean_role_name(role_name)
    if not target:
        return None

    visited: set[str] = set()
    current = target
    while current:
        if current in visited:
            return None
        visited.add(current)

        role_cfg = roles.get(current)
        if not isinstance(role_cfg, dict):
            return None

        provider = _clean_text(role_cfg.get("provider"))
        model = _clean_text(role_cfg.get("model"))
        if provider and model:
            return {"provider": provider, "model": model, "role": target}

        inherit = _clean_role_name(role_cfg.get("inherit"))
        if not inherit:
            return None
        current = inherit

    return None


def _build_resolved(
    provider: str,
    model: str,
    *,
    role: Optional[str],
    tier: Optional[str] = None,
    source: ResolutionSource,
    fallback_used: bool = False,
    upgrade_trigger: Optional[str] = None,
) -> ResolvedModel:
    return ResolvedModel(
        provider=provider,
        model=model,
        role=role,
        tier=tier,
        resolution_source=source,
        fallback_used=fallback_used,
        upgrade_trigger=upgrade_trigger,
    )


def resolve_runtime_model(
    context: RoutingContext,
    *,
    role_lookup: Optional[Callable[[str], Optional[dict[str, str]]]] = None,
    tier_lookup: Optional[Callable[[str], Optional[dict[str, str]]]] = None,
    default_provider: str = "openai",
    default_model: str = "gpt-4o",
) -> ResolvedModel:
    request_provider = _clean_text(context.request_provider)
    request_model = _clean_text(context.request_model)
    request_role = _clean_role_name(context.request_model_role)
    agent_provider = _clean_text(context.agent_provider)
    agent_model = _clean_text(context.agent_model)
    selection_mode = _clean_text(context.agent_model_selection_mode) or "direct"
    agent_tier = _clean_role_name(context.agent_model_tier)
    agent_role = _clean_role_name(context.agent_model_role)
    policy = _clean_role_name(context.agent_model_policy) or "prefer_role"
    routing_default_mode = _clean_role_name(context.routing_default_mode) or "legacy"
    fallback_policy = _clean_role_name(context.routing_fallback_policy) or "use_legacy_agent_model"
    tool_role_name = _clean_role_name(context.tool_call_requires_role) or "tool_use"
    multi_skill_role_name = _clean_role_name(context.multi_skill_requires_role) or "reasoning"
    auto_upgrade_enabled = bool(context.auto_upgrade_enabled)
    upgrade_on_tools = bool(context.upgrade_on_tools)
    upgrade_on_multi_skill = bool(context.upgrade_on_multi_skill)

    # 1) explicit provider/model on request always wins
    if request_provider and request_model:
        return _build_resolved(
            request_provider,
            request_model,
            role=request_role,
            source=ResolutionSource.REQUEST_OVERRIDE,
        )

    # 1b) partial explicit override from request
    if request_provider and not request_model:
        return _build_resolved(
            request_provider,
            default_model,
            role=request_role,
            source=ResolutionSource.REQUEST_OVERRIDE,
            fallback_used=True,
        )
    if request_model and not request_provider:
        return _build_resolved(
            default_provider,
            request_model,
            role=request_role,
            source=ResolutionSource.REQUEST_OVERRIDE,
            fallback_used=True,
        )

    # 2) explicit role on request
    if request_role and role_lookup:
        role_config = role_lookup(request_role)
        if role_config:
            return _build_resolved(
                role_config["provider"],
                role_config["model"],
                role=request_role,
                source=ResolutionSource.REQUEST_OVERRIDE,
            )

    # 3) agent tier
    if selection_mode == "tier" and agent_tier and tier_lookup:
        tier_config = tier_lookup(agent_tier)
        if tier_config:
            return _build_resolved(
                tier_config["provider"],
                tier_config["model"],
                role=agent_role,
                tier=agent_tier,
                source=ResolutionSource.AGENT_TIER,
            )

    # 4) agent preferred role
    prefer_agent_role = policy == "prefer_role" or (policy == "system_default" and routing_default_mode == "role_based")
    if prefer_agent_role and agent_role and role_lookup:
        role_config = role_lookup(agent_role)
        if role_config:
            return _build_resolved(
                role_config["provider"],
                role_config["model"],
                role=agent_role,
                source=ResolutionSource.AGENT_ROLE,
            )

    # 5) direct model on agent
    if (selection_mode == "direct" or policy == "force_direct") and agent_provider and agent_model:
        return _build_resolved(
            agent_provider,
            agent_model,
            role=agent_role,
            source=ResolutionSource.LEGACY_AGENT_MODEL,
        )

    # 6) auto-upgrade based on tool/skill complexity
    if auto_upgrade_enabled and role_lookup:
        if upgrade_on_tools and (context.has_tools or context.selected_tool_count > 0):
            role_config = role_lookup(tool_role_name)
            if role_config:
                return _build_resolved(
                    role_config["provider"],
                    role_config["model"],
                    role=tool_role_name,
                    source=ResolutionSource.AUTO_UPGRADE,
                    upgrade_trigger="tools",
                )
        if upgrade_on_multi_skill and context.skill_count > 1:
            role_config = role_lookup(multi_skill_role_name)
            if role_config:
                return _build_resolved(
                    role_config["provider"],
                    role_config["model"],
                    role=multi_skill_role_name,
                    source=ResolutionSource.AUTO_UPGRADE,
                    upgrade_trigger="multi_skill",
                )

    # 7) fallback policy
    if fallback_policy == "use_general_chat" and role_lookup:
        role_config = role_lookup("general_chat")
        if role_config:
            return _build_resolved(
                role_config["provider"],
                role_config["model"],
                role="general_chat",
                source=ResolutionSource.SYSTEM_ROLE,
                fallback_used=True,
            )

    if fallback_policy == "use_legacy_agent_model" and agent_provider and agent_model:
        return _build_resolved(
            agent_provider,
            agent_model,
            role=agent_role,
            source=ResolutionSource.LEGACY_AGENT_MODEL,
            fallback_used=True,
        )

    # 8) system role fallback
    if role_lookup:
        role_config = role_lookup("general_chat")
        if role_config:
            return _build_resolved(
                role_config["provider"],
                role_config["model"],
                role="general_chat",
                source=ResolutionSource.SYSTEM_ROLE,
                fallback_used=True,
            )

    # 9) global default fallback
    return _build_resolved(
        default_provider,
        default_model,
        role=None,
        source=ResolutionSource.LEGACY_GLOBAL_DEFAULT,
        fallback_used=True,
    )
