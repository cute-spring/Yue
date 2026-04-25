"""Minimal same-stack host integration example for Skill Runtime Core.

This example shows how a host project can:
1. register host runtime adapters (agent/group/feature flags + env config mapping)
2. build a bootstrap spec once
3. mount runtime routes with one call
"""

from __future__ import annotations

from fastapi import FastAPI

from app.services.skill_service import register_stage4_lite_host_runtime_adapter_bundle
from app.services.skills import (
    EnvHostConfigAdapter,
    HostRuntimeAdapterBundle,
    bootstrap_skill_runtime_app,
    build_default_host_runtime_adapter_bundle,
    build_skill_runtime_bootstrap_spec_from_env,
)


class InMemoryAgentStore:
    def get_agent(self, _agent_id: str):
        return None


class StaticConfigService:
    def get_feature_flags(self):
        return {
            "skill_runtime_enabled": True,
            "skill_import_auto_activate_enabled": True,
        }


class InMemorySkillGroupStore:
    def get_skill_refs_by_group_ids(self, _group_ids):
        return []


def build_host_runtime_bundle() -> HostRuntimeAdapterBundle:
    # Map host-specific env keys to neutral runtime keys.
    host_config = EnvHostConfigAdapter(
        key_aliases={
            "SKILL_RUNTIME_DATA_DIR": ("HOST_RUNTIME_DATA_DIR", "SKILL_RUNTIME_DATA_DIR"),
            "SKILL_RUNTIME_API_PREFIX": ("HOST_RUNTIME_API_PREFIX", "SKILL_RUNTIME_API_PREFIX"),
        }
    )
    return build_default_host_runtime_adapter_bundle(
        agent_store=InMemoryAgentStore(),
        config_service=StaticConfigService(),
        skill_group_store=InMemorySkillGroupStore(),
        host_config_provider=host_config,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Host App with Skill Runtime Core")

    bundle = build_host_runtime_bundle()
    register_stage4_lite_host_runtime_adapter_bundle(bundle)

    bootstrap_spec = build_skill_runtime_bootstrap_spec_from_env(
        host_config_adapter=bundle.host_config_provider
    )
    bootstrap_skill_runtime_app(app, bootstrap_spec=bootstrap_spec)
    return app


app = create_app()
