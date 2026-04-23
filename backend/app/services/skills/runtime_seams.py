from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from app.services.skills.import_models import SkillImportLifecycleState
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec, SkillSpec
from app.services.skills.policy import SkillPolicyGate
from app.services.skills.runtime_catalog import RuntimeSkillCatalogProjector


class ToolCapabilityProvider(Protocol):
    def resolve_effective_tools(self, *, agent_tools: Sequence[str], skill: SkillSpec | None) -> list[str]:
        ...


class ActivationStateStore(Protocol):
    def list_active_source_refs(self) -> list[str]:
        ...


class RuntimeCatalogProjector(Protocol):
    def project_active_import_dirs(self) -> list[SkillDirectorySpec]:
        ...


class PromptInjectionAdapter(Protocol):
    def compose_prompt(self, *, base_prompt: str, skill_prompt: str | None) -> str:
        ...


class VisibilityResolver(Protocol):
    def resolve_visible_skill_refs(self, agent: Any) -> list[str]:
        ...


class DefaultToolCapabilityProvider:
    def resolve_effective_tools(self, *, agent_tools: Sequence[str], skill: SkillSpec | None) -> list[str]:
        allowed_tools = skill.constraints.allowed_tools if skill and skill.constraints else None
        return SkillPolicyGate.check_tool_intersection(list(agent_tools), allowed_tools)


class ImportStoreActivationStateStore:
    def __init__(self, import_store: SkillImportStore):
        self.import_store = import_store

    def list_active_source_refs(self) -> list[str]:
        refs: list[str] = []
        seen = set()
        for entry in self.import_store.list_entries():
            record = entry.record
            if record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
                continue
            source_ref = str(record.source_ref or "").strip()
            if not source_ref or source_ref in seen:
                continue
            seen.add(source_ref)
            refs.append(source_ref)
        return refs


class ImportGateRuntimeCatalogProjector:
    def __init__(self, import_store: SkillImportStore):
        self._projector = RuntimeSkillCatalogProjector(import_store=import_store)

    def project_active_import_dirs(self) -> list[SkillDirectorySpec]:
        return self._projector.project_active_import_dirs()


class DefaultPromptInjectionAdapter:
    def compose_prompt(self, *, base_prompt: str, skill_prompt: str | None) -> str:
        base = base_prompt or ""
        if not skill_prompt:
            return base
        if not base.strip():
            return skill_prompt
        return f"{base.rstrip()}\n\n{skill_prompt.lstrip()}"


class RouterVisibilityResolver:
    def __init__(self, router: Any):
        self.router = router

    def resolve_visible_skill_refs(self, agent: Any) -> list[str]:
        return list(self.router.resolve_visible_skill_refs(agent))


@dataclass(frozen=True)
class SkillRuntimeSeams:
    tool_capability_provider: ToolCapabilityProvider
    activation_state_store: ActivationStateStore
    runtime_catalog_projector: RuntimeCatalogProjector
    prompt_injection_adapter: PromptInjectionAdapter
    visibility_resolver: VisibilityResolver


def build_skill_runtime_seams(*, import_store: SkillImportStore, router: Any) -> SkillRuntimeSeams:
    return SkillRuntimeSeams(
        tool_capability_provider=DefaultToolCapabilityProvider(),
        activation_state_store=ImportStoreActivationStateStore(import_store),
        runtime_catalog_projector=ImportGateRuntimeCatalogProjector(import_store),
        prompt_injection_adapter=DefaultPromptInjectionAdapter(),
        visibility_resolver=RouterVisibilityResolver(router),
    )
