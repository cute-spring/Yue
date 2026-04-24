from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

# Host adapter layer for runtime visibility and host-owned dependencies. The
# protocols are reusable; the default resolver/bundle helpers preserve Yue's
# current semantics for copy-first adoption.


class AgentProvider(Protocol):
    def get_agent(self, agent_id: str) -> Any | None:
        ...


class FeatureFlagProvider(Protocol):
    def get_feature_flags(self) -> dict[str, Any]:
        ...


class SkillGroupResolver(Protocol):
    def get_skill_refs_by_group_ids(self, group_ids: list[str]) -> list[str]:
        ...


class AgentVisibilityResolver(Protocol):
    def resolve_visible_skill_refs(self, agent: Any) -> list[str]:
        ...


class HostConfigProvider(Protocol):
    def get(self, key: str) -> str | None:
        ...


def _dedupe_skill_refs(refs: list[Any]) -> list[str]:
    deduped: list[str] = []
    seen = set()
    for ref in refs:
        if not isinstance(ref, str):
            continue
        normalized = ref.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


@dataclass(frozen=True)
class StoreBackedAgentProvider:
    store: Any

    def get_agent(self, agent_id: str) -> Any | None:
        return self.store.get_agent(agent_id)


@dataclass(frozen=True)
class ConfigFeatureFlagProvider:
    config_service: Any

    def get_feature_flags(self) -> dict[str, Any]:
        return dict(self.config_service.get_feature_flags() or {})


@dataclass(frozen=True)
class GroupStoreSkillGroupResolver:
    store: Any

    def get_skill_refs_by_group_ids(self, group_ids: list[str]) -> list[str]:
        return list(self.store.get_skill_refs_by_group_ids(group_ids))


@dataclass
class GroupAwareAgentVisibilityResolver:
    # Yue-flavored host adapter: combines agent-local visible refs with
    # host-owned group resolution so routing core can stay group-store agnostic.
    skill_group_resolver: SkillGroupResolver | None = None

    @property
    def skill_group_store(self) -> Any:
        return self.skill_group_resolver

    @skill_group_store.setter
    def skill_group_store(self, store: Any) -> None:
        self.skill_group_resolver = store

    def resolve_visible_skill_refs(self, agent: Any) -> list[str]:
        refs: list[Any] = []
        pre_resolved_refs = getattr(agent, "resolved_visible_skills", None) or []
        refs.extend(pre_resolved_refs)
        if not pre_resolved_refs and self.skill_group_resolver is not None:
            selected_group_ids = getattr(agent, "skill_groups", None) or []
            refs.extend(self.skill_group_resolver.get_skill_refs_by_group_ids(selected_group_ids))
        if not pre_resolved_refs:
            refs.extend(getattr(agent, "extra_visible_skills", None) or [])
            refs.extend(getattr(agent, "visible_skills", None) or [])
        return _dedupe_skill_refs(refs)


@dataclass(frozen=True)
class HostRuntimeAdapterBundle:
    # Copy-first convenience bundle for host wiring; pure core extraction should
    # keep the protocols while allowing hosts to assemble this contract locally.
    agent_provider: AgentProvider
    feature_flag_provider: FeatureFlagProvider
    skill_group_resolver: SkillGroupResolver
    visibility_resolver: AgentVisibilityResolver | None = None
    host_config_provider: HostConfigProvider | None = None


def build_default_host_runtime_adapter_bundle(
    *,
    agent_store: Any,
    config_service: Any,
    skill_group_store: Any,
    host_config_provider: HostConfigProvider | None = None,
) -> HostRuntimeAdapterBundle:
    group_resolver = GroupStoreSkillGroupResolver(skill_group_store)
    return HostRuntimeAdapterBundle(
        agent_provider=StoreBackedAgentProvider(agent_store),
        feature_flag_provider=ConfigFeatureFlagProvider(config_service),
        skill_group_resolver=group_resolver,
        visibility_resolver=GroupAwareAgentVisibilityResolver(skill_group_resolver=group_resolver),
        host_config_provider=host_config_provider,
    )
