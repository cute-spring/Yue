from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

from app.services.skills import SkillActionExecutionService, SkillRegistry


_ACTION_PREVIEW_PATTERN = re.compile(
    r"```jira-action-preview\s*(\{.*?\})\s*```",
    re.DOTALL,
)

_SUPPORTED_ACTIONS = {
    "add_comment",
    "create_issue",
    "update_issue",
    "transition_issue",
}


@dataclass(frozen=True)
class JiraActionPreview:
    action_id: str
    arguments: dict[str, Any]
    reason: str | None = None


def extract_jira_action_preview(response: str) -> Optional[JiraActionPreview]:
    if not isinstance(response, str) or not response.strip():
        return None

    match = _ACTION_PREVIEW_PATTERN.search(response)
    if match is None:
        return None

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    action_id = payload.get("action")
    arguments = payload.get("args")
    reason = payload.get("reason")

    if action_id not in _SUPPORTED_ACTIONS:
        return None
    if not isinstance(arguments, dict) or not arguments:
        return None
    if reason is not None and not isinstance(reason, str):
        return None

    return JiraActionPreview(
        action_id=action_id,
        arguments=arguments,
        reason=reason.strip() or None if isinstance(reason, str) else None,
    )


def find_agent_jira_skill_ref(agent: Any) -> Optional[str]:
    if agent is None:
        return None

    candidates = []
    for attr in ("resolved_visible_skills", "extra_visible_skills", "visible_skills"):
        values = getattr(agent, attr, None) or []
        if isinstance(values, list):
            candidates.extend(values)

    for item in candidates:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized.startswith("jira:") or normalized == "jira":
            return normalized
    return None


@lru_cache(maxsize=1)
def _load_repo_jira_runtime() -> tuple[SkillRegistry, SkillActionExecutionService]:
    repo_root = Path(__file__).resolve().parents[4]
    registry = SkillRegistry(skill_dirs=[str(repo_root / "data" / "skills")])
    registry.load_all()
    return registry, SkillActionExecutionService(registry)


def resolve_repo_jira_skill_runtime(
    skill_ref: str,
    *,
    provider: str | None = None,
    model_name: str | None = None,
) -> tuple[Any | None, SkillActionExecutionService | None]:
    if not isinstance(skill_ref, str) or not skill_ref.strip():
        return None, None
    if ":" in skill_ref:
        skill_name, skill_version = skill_ref.split(":", 1)
    else:
        skill_name, skill_version = skill_ref, None
    if skill_name.strip() != "jira":
        return None, None

    registry, service = _load_repo_jira_runtime()
    skill = registry.get_full_skill(
        skill_name.strip(),
        skill_version.strip() if isinstance(skill_version, str) and skill_version.strip() else None,
        provider=provider,
        model_name=model_name,
    )
    if skill is None:
        skill = registry.get_skill(
            skill_name.strip(),
            skill_version.strip() if isinstance(skill_version, str) and skill_version.strip() else None,
        )
    if skill is None:
        return None, None
    return skill, service
