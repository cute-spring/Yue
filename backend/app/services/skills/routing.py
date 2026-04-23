import re
from typing import Any, Dict, List, Optional

from app.services.skill_group_store import skill_group_store as default_skill_group_store
from app.services.skills.models import SkillSpec


class AgentVisibilityResolver:
    """
    Yue-specific visibility resolver kept as an adapter around group-store semantics.
    Routing/scoring stays in SkillRouter.
    """

    def __init__(self, skill_group_store: Any = None):
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


class SkillRouter:
    """
    Agent-scoped skill filtering, ranking, and fallback.
    """

    def __init__(self, registry: Any, skill_group_store: Any = None, visibility_resolver: Any = None):
        self.registry = registry
        base_store = skill_group_store or default_skill_group_store
        self.visibility_resolver = visibility_resolver or AgentVisibilityResolver(base_store)
        self._legacy_skill_group_store = base_store

    @property
    def skill_group_store(self) -> Any:
        resolver = self.visibility_resolver
        if hasattr(resolver, "skill_group_store"):
            return resolver.skill_group_store
        return self._legacy_skill_group_store

    @skill_group_store.setter
    def skill_group_store(self, store: Any) -> None:
        self._legacy_skill_group_store = store or default_skill_group_store
        resolver = self.visibility_resolver
        if hasattr(resolver, "skill_group_store"):
            resolver.skill_group_store = self._legacy_skill_group_store

    def resolve_visible_skill_refs(self, agent: Any) -> List[str]:
        resolver = self.visibility_resolver
        if hasattr(resolver, "resolve_visible_skill_refs"):
            return list(resolver.resolve_visible_skill_refs(agent))
        if callable(resolver):
            return list(resolver(agent))
        return []

    def get_visible_skills(self, agent: Any) -> List[SkillSpec]:
        visible_refs = self.resolve_visible_skill_refs(agent)
        if not visible_refs:
            return []

        visible = []
        for name_version in visible_refs:
            name, version = self._split_skill_ref(name_version)
            skill = self.registry.get_skill(name, version)
            if skill:
                visible.append(skill)
        return visible

    def _split_skill_ref(self, skill_ref: str) -> tuple[str, Optional[str]]:
        if ":" in skill_ref:
            return tuple(skill_ref.split(":", 1))
        return skill_ref, None

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

    def route_with_contract(self, agent: Any, task: str, requested_skill: str = None) -> Dict[str, Any]:
        visible_refs = self.resolve_visible_skill_refs(agent)
        visible_skills = self.get_visible_skills(agent)
        effective_requested_skill = requested_skill or self.infer_requested_skill(agent, task)
        selected_skill = self.route(agent, task, requested_skill=requested_skill)
        visible_skill_map = {
            f"{skill.name}:{skill.version}": skill
            for skill in visible_skills
        }
        visible_entries: List[Dict[str, Any]] = []
        for ref in visible_refs:
            ref_name, ref_version = self._split_skill_ref(ref)
            resolved_skill = visible_skill_map.get(ref) or next(
                (
                    skill for skill in visible_skills
                    if skill.name == ref_name and (ref_version is None or skill.version == ref_version)
                ),
                None,
            )
            visible_entries.append({
                "name": ref_name,
                "version": ref_version or (resolved_skill.version if resolved_skill else None),
                "skill": resolved_skill,
                "available": resolved_skill.availability is not False if resolved_skill else True,
            })
        if not visible_entries and selected_skill is not None:
            visible_entries.append({
                "name": selected_skill.name,
                "version": selected_skill.version,
                "skill": selected_skill,
                "available": selected_skill.availability is not False,
            })

        score_rows: List[Dict[str, Any]] = []
        if effective_requested_skill:
            if ":" in effective_requested_skill:
                req_name, req_version = effective_requested_skill.split(":", 1)
            else:
                req_name, req_version = effective_requested_skill, None
            for entry in visible_entries:
                matches_request = entry["name"] == req_name and (not req_version or entry["version"] == req_version)
                score_rows.append({
                    "name": entry["name"],
                    "version": entry["version"],
                    "score": 1000 if matches_request and entry["available"] else 0,
                    "available": entry["available"],
                    "visible": True,
                })
        else:
            task_text = (task or "").lower()
            task_tokens = set(self._tokenize_ascii(task or ""))
            task_cjk = set(self._tokenize_cjk(task or ""))
            for entry in visible_entries:
                skill = entry["skill"]
                score_rows.append({
                    "name": entry["name"],
                    "version": entry["version"],
                    "score": self._score_skill(skill, task_text, task_tokens, task_cjk)
                    if skill is not None and entry["available"] else 0,
                    "available": entry["available"],
                    "visible": True,
                })

        score_rows.sort(key=lambda item: (-item["score"], item["name"], item["version"]))
        selected_entry = None
        if selected_skill is not None:
            for row in score_rows:
                if row["name"] == selected_skill.name and row["version"] == selected_skill.version:
                    selected_entry = row
                    break

        selected_payload = None
        if selected_skill is not None:
            selected_payload = {
                "name": selected_skill.name,
                "version": selected_skill.version,
                "score": selected_entry["score"] if selected_entry else 0,
            }

        reason_code = "skill_selected" if selected_skill is not None else "no_matching_skill"
        fallback_used = selected_skill is None
        stage_trace: List[Dict[str, Any]] = [
            {
                "stage": "resolve_visible_skills",
                "status": "completed",
                "visible_skill_refs": visible_refs,
            }
        ]
        if not effective_requested_skill:
            top_candidate = None
            if score_rows:
                top_candidate = {
                    "name": score_rows[0]["name"],
                    "version": score_rows[0]["version"],
                    "score": score_rows[0]["score"],
                }
            stage_trace.append({
                "stage": "score_candidates",
                "status": "completed",
                "top_candidate": top_candidate,
            })
        if selected_skill is not None:
            stage_trace.append({
                "stage": "apply_selection",
                "status": "completed",
                "selected": {"name": selected_skill.name, "version": selected_skill.version},
            })
        else:
            stage_trace.append({
                "stage": "fallback",
                "status": "completed",
                "reason_code": reason_code,
            })

        return {
            "selected": selected_payload,
            "candidates": [
                {"name": row["name"], "version": row["version"], "score": row["score"]}
                for row in score_rows
                if selected_skill is not None and row["available"]
            ],
            "scores": score_rows,
            "reason": {
                "code": reason_code,
                "requested_skill": effective_requested_skill,
                "fallback_used": fallback_used,
            },
            "fallback_used": fallback_used,
            "stage_trace": stage_trace,
        }

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
