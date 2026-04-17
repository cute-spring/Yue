from app.services.llm.routing import (
    ResolutionSource,
    RoutingContext,
    resolve_role_config,
    resolve_runtime_model,
)


def _role_lookup(name: str):
    routing = {
        "roles": {
            "general_chat": {"provider": "openai", "model": "gpt-4o-mini"},
            "tool_use": {"provider": "openai", "model": "gpt-4o"},
            "reasoning": {"inherit": "tool_use"},
        }
    }
    return resolve_role_config(routing, name)


def test_resolve_role_config_with_inherit():
    routing = {
        "roles": {
            "general_chat": {"provider": "openai", "model": "gpt-4o-mini"},
            "reasoning": {"inherit": "general_chat"},
        }
    }
    resolved = resolve_role_config(routing, "reasoning")
    assert resolved is not None
    assert resolved["provider"] == "openai"
    assert resolved["model"] == "gpt-4o-mini"
    assert resolved["role"] == "reasoning"


def test_resolve_runtime_model_prefers_explicit_request_provider_model():
    resolved = resolve_runtime_model(
        RoutingContext(
            request_provider="deepseek",
            request_model="deepseek-chat",
            agent_provider="openai",
            agent_model="gpt-4o",
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.provider == "deepseek"
    assert resolved.model == "deepseek-chat"
    assert resolved.resolution_source == ResolutionSource.REQUEST_OVERRIDE


def test_resolve_runtime_model_keeps_request_provider_when_model_missing():
    resolved = resolve_runtime_model(
        RoutingContext(
            request_provider="ollama",
            request_model=None,
        ),
        role_lookup=_role_lookup,
        default_provider="openai",
        default_model="gpt-4o-mini",
    )
    assert resolved.provider == "ollama"
    assert resolved.model == "gpt-4o-mini"
    assert resolved.resolution_source == ResolutionSource.REQUEST_OVERRIDE


def test_resolve_runtime_model_uses_agent_role_when_present():
    resolved = resolve_runtime_model(
        RoutingContext(
            agent_model_role="reasoning",
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o"
    assert resolved.role == "reasoning"
    assert resolved.resolution_source == ResolutionSource.AGENT_ROLE


def test_resolve_runtime_model_auto_upgrades_for_tools():
    resolved = resolve_runtime_model(
        RoutingContext(
            has_tools=True,
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.role == "tool_use"
    assert resolved.upgrade_trigger == "tools"
    assert resolved.resolution_source == ResolutionSource.AUTO_UPGRADE


def test_resolve_runtime_model_respects_force_direct_policy():
    resolved = resolve_runtime_model(
        RoutingContext(
            agent_provider="deepseek",
            agent_model="deepseek-chat",
            agent_model_role="reasoning",
            agent_model_policy="force_direct",
            has_tools=True,
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.provider == "deepseek"
    assert resolved.model == "deepseek-chat"
    assert resolved.resolution_source == ResolutionSource.LEGACY_AGENT_MODEL


def test_resolve_runtime_model_prefers_agent_role_before_direct_model_when_policy_is_prefer_role():
    resolved = resolve_runtime_model(
        RoutingContext(
            agent_provider="anthropic",
            agent_model="claude-3-7-sonnet",
            agent_model_role="reasoning",
            agent_model_selection_mode="direct",
            agent_model_tier="heavy",
        ),
        role_lookup=_role_lookup,
        tier_lookup=lambda name: {"provider": "openai", "model": f"tier-{name}"},
    )
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o"
    assert resolved.role == "reasoning"
    assert resolved.resolution_source == ResolutionSource.AGENT_ROLE


def test_resolve_runtime_model_uses_agent_tier_before_agent_role():
    resolved = resolve_runtime_model(
        RoutingContext(
            agent_provider="openai",
            agent_model="gpt-4o-mini",
            agent_model_role="reasoning",
            agent_model_selection_mode="tier",
            agent_model_tier="heavy",
        ),
        role_lookup=_role_lookup,
        tier_lookup=lambda name: {"provider": "anthropic", "model": f"claude-{name}"},
    )
    assert resolved.provider == "anthropic"
    assert resolved.model == "claude-heavy"
    assert resolved.tier == "heavy"
    assert resolved.resolution_source == ResolutionSource.AGENT_TIER


def test_resolve_runtime_model_falls_back_to_agent_role_when_tier_missing():
    resolved = resolve_runtime_model(
        RoutingContext(
            agent_model_role="reasoning",
            agent_model_selection_mode="tier",
            agent_model_tier="heavy",
        ),
        role_lookup=_role_lookup,
        tier_lookup=lambda _name: None,
    )
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o"
    assert resolved.role == "reasoning"
    assert resolved.resolution_source == ResolutionSource.AGENT_ROLE


def test_resolve_runtime_model_falls_back_to_global_default_without_role_lookup():
    resolved = resolve_runtime_model(
        RoutingContext(),
        role_lookup=None,
        default_provider="openai",
        default_model="gpt-4o-mini",
    )
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o-mini"
    assert resolved.fallback_used is True
    assert resolved.resolution_source == ResolutionSource.LEGACY_GLOBAL_DEFAULT


def test_resolve_runtime_model_respects_auto_upgrade_and_rule_names():
    resolved = resolve_runtime_model(
        RoutingContext(
            has_tools=True,
            tool_call_requires_role="reasoning",
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o"
    assert resolved.role == "reasoning"
    assert resolved.upgrade_trigger == "tools"


def test_resolve_runtime_model_skips_auto_upgrade_when_agent_opt_out_is_disabled():
    resolved = resolve_runtime_model(
        RoutingContext(
            has_tools=True,
            upgrade_on_tools=False,
            agent_provider="anthropic",
            agent_model="claude-3-7-sonnet",
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.provider == "anthropic"
    assert resolved.model == "claude-3-7-sonnet"
    assert resolved.resolution_source == ResolutionSource.LEGACY_AGENT_MODEL


def test_resolve_runtime_model_uses_general_chat_fallback_policy():
    resolved = resolve_runtime_model(
        RoutingContext(
            routing_fallback_policy="use_general_chat",
            agent_provider="anthropic",
            agent_model="claude-3-7-sonnet",
            auto_upgrade_enabled=False,
        ),
        role_lookup=_role_lookup,
    )
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o-mini"
    assert resolved.role == "general_chat"
    assert resolved.resolution_source == ResolutionSource.SYSTEM_ROLE
