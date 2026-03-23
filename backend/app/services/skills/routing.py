import re
from typing import Any, List, Optional

from app.services.skill_group_store import skill_group_store as default_skill_group_store
from app.services.skills.models import SkillSpec


class SkillRouter:
    """
    Agent-scoped skill filtering, ranking, and fallback.
    """

    def __init__(self, registry: Any, skill_group_store: Any = None):
        self.registry = registry
        self.skill_group_store = skill_group_store or default_skill_group_store

    def resolve_visible_skill_refs(self, agent: Any) -> List[str]:
        refs: List[str] = []
        pre_resolved_refs = getattr(agent, "resolved_visible_skills", None) or []
        refs.extend(pre_resolved_refs)
        selected_group_ids = getattr(agent, "skill_groups", None) or []
        if not pre_resolved_refs:
            refs.extend(self.skill_group_store.get_skill_refs_by_group_ids(selected_group_ids))
        extra_refs = getattr(agent, "extra_visible_skills", None) or []
        if not pre_resolved_refs:
            refs.extend(extra_refs)
        legacy_refs = getattr(agent, "visible_skills", None) or []
        if not pre_resolved_refs:
            refs.extend(legacy_refs)
        deduped: List[str] = []
        seen = set()
        for ref in refs:
            if not isinstance(ref, str):
                continue
            norm = ref.strip()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            deduped.append(norm)
        return deduped

    def get_visible_skills(self, agent: Any) -> List[SkillSpec]:
        visible_refs = self.resolve_visible_skill_refs(agent)
        if not visible_refs:
            return []

        visible = []
        for name_version in visible_refs:
            if ":" in name_version:
                name, version = name_version.split(":", 1)
            else:
                name, version = name_version, None

            skill = self.registry.get_skill(name, version)
            if skill:
                visible.append(skill)
        return visible

    def _tokenize_ascii(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _tokenize_cjk(self, text: str) -> List[str]:
        return re.findall(r"[\u4e00-\u9fff]{2,}", text)

    def _score_skill(self, skill: SkillSpec, task_text: str, task_tokens: set, task_cjk: set) -> int:
        score = 0
        name = skill.name or ""
        description = skill.description or ""
        capabilities = skill.capabilities or []

        name_lower = name.lower()
        if name_lower and name_lower in task_text:
            score += 6

        name_tokens = set(self._tokenize_ascii(name))
        score += 3 * len(name_tokens.intersection(task_tokens))

        desc_tokens = set(self._tokenize_ascii(description))
        score += len(desc_tokens.intersection(task_tokens))

        desc_cjk = set(self._tokenize_cjk(description))
        score += len(desc_cjk.intersection(task_cjk))

        for cap in capabilities:
            cap_text = cap or ""
            cap_lower = cap_text.lower()
            if cap_lower and cap_lower in task_text:
                score += 5
            cap_tokens = set(self._tokenize_ascii(cap_text))
            score += 2 * len(cap_tokens.intersection(task_tokens))
            cap_cjk = set(self._tokenize_cjk(cap_text))
            score += 2 * len(cap_cjk.intersection(task_cjk))

        return score

    def score_skill(self, skill: SkillSpec, task: str) -> int:
        task_text = (task or "").lower()
        task_tokens = set(self._tokenize_ascii(task or ""))
        task_cjk = set(self._tokenize_cjk(task or ""))
        return self._score_skill(skill, task_text, task_tokens, task_cjk)

    def infer_requested_skill(self, agent: Any, task: str) -> Optional[str]:
        task_text = (task or "").strip().lower()
        if not task_text:
            return None
        visible_skills = self.get_visible_skills(agent)
        available_skills = [s for s in visible_skills if s.availability is not False]
        candidates: List[tuple[int, str]] = []
        for skill in available_skills:
            name = (skill.name or "").lower()
            if not name:
                continue
            name_version = f"{skill.name}:{skill.version}"
            if name_version.lower() in task_text:
                candidates.append((len(name_version), name_version))
                continue
            if name in task_text:
                candidates.append((len(name), name_version))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    def route_with_score(self, agent: Any, task: str, requested_skill: str = None) -> tuple[Optional[SkillSpec], int]:
        visible_skills = self.get_visible_skills(agent)
        available_skills = [s for s in visible_skills if s.availability is not False]
        if not visible_skills:
            return None, 0
        effective_requested_skill = requested_skill or self.infer_requested_skill(agent, task)
        if effective_requested_skill:
            if ":" in effective_requested_skill:
                req_name, req_version = effective_requested_skill.split(":", 1)
            else:
                req_name, req_version = effective_requested_skill, None
            for skill in available_skills:
                if skill.name == req_name and (not req_version or skill.version == req_version):
                    return skill, 1000
            return None, 0
        task_text = (task or "").lower()
        task_tokens = set(self._tokenize_ascii(task or ""))
        task_cjk = set(self._tokenize_cjk(task or ""))
        scored = [(self._score_skill(skill, task_text, task_tokens, task_cjk), skill) for skill in available_skills]
        scored.sort(key=lambda item: (-item[0], item[1].name))
        if scored and scored[0][0] > 0:
            return scored[0][1], scored[0][0]
        return None, 0

    def route(self, agent: Any, task: str, requested_skill: str = None) -> Optional[SkillSpec]:
        skill, _score = self.route_with_score(agent, task, requested_skill=requested_skill)
        return skill
