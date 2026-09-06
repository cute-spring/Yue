from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.services.agent_store import AgentConfig
from app.services.skills.models import SkillSpec


InstructionReviewTargetType = Literal["skill", "agent"]
InstructionReviewStatus = Literal["pass", "warning", "blocker"]


class InstructionReviewTarget(BaseModel):
    target_type: InstructionReviewTargetType
    name: str
    version: Optional[str] = None
    source_ref: Optional[str] = None


class InstructionReviewFinding(BaseModel):
    code: str
    title: str
    detail: str
    recommendation: str


class InstructionReviewRubricItem(BaseModel):
    key: str
    label: str
    status: InstructionReviewStatus
    findings: list[InstructionReviewFinding] = Field(default_factory=list)


class InstructionReviewReport(BaseModel):
    target: InstructionReviewTarget
    advisory_only: bool = True
    mutates_target: bool = False
    review_scope: list[str]
    summary: str
    overall_status: InstructionReviewStatus
    rubric: list[InstructionReviewRubricItem]
    blockers: list[InstructionReviewFinding] = Field(default_factory=list)
    recommendations: list[InstructionReviewFinding] = Field(default_factory=list)
    yue_runtime_positioning: str = (
        "Yue is reviewing runtime and workbench fit only; it is not acting as a full skill authoring IDE."
    )


class InstructionReviewService:
    """Deterministic admin-facing review for one skill or agent prompt."""

    REVIEW_SCOPE = [
        "trigger_clarity",
        "activation_risk",
        "context_loading",
        "tool_policy",
        "safety_boundaries",
        "examples_quality",
        "yue_runtime_fit",
    ]

    def review_skill(self, skill: SkillSpec) -> InstructionReviewReport:
        target = InstructionReviewTarget(
            target_type="skill",
            name=skill.name,
            version=skill.version,
            source_ref=skill.source_path or skill.source_dir or skill.manifest_path,
        )
        text = self._join_text(
            skill.description,
            " ".join(skill.capabilities or []),
            skill.system_prompt,
            skill.instructions,
            skill.examples,
            skill.failure_handling,
        )
        metadata = {
            "allowed_tools": list(getattr(skill.constraints, "allowed_tools", None) or []),
            "has_allowed_tools": bool(getattr(skill.constraints, "allowed_tools", None) is not None),
            "always": bool(skill.always),
            "actions": [],
            "references": [],
            "scripts": [],
            "max_tokens": getattr(skill.constraints, "max_tokens", None),
            "examples": skill.examples,
            "source_layer": skill.source_layer,
        }
        return self._build_report(target=target, text=text, metadata=metadata)

    def review_agent(self, agent: AgentConfig) -> InstructionReviewReport:
        target = InstructionReviewTarget(
            target_type="agent",
            name=agent.name,
            version=None,
            source_ref=agent.id,
        )
        metadata = {
            "allowed_tools": list(agent.enabled_tools or []),
            "has_allowed_tools": bool(agent.enabled_tools),
            "always": getattr(agent, "skill_mode", "off") == "auto",
            "actions": [],
            "references": [],
            "scripts": [],
            "max_tokens": None,
            "examples": None,
            "source_layer": "agent",
        }
        return self._build_report(target=target, text=agent.system_prompt or "", metadata=metadata)

    def review_prompt(
        self,
        *,
        target_type: InstructionReviewTargetType,
        name: str,
        prompt: str,
        allowed_tools: Optional[list[str]] = None,
        source_ref: Optional[str] = None,
    ) -> InstructionReviewReport:
        target = InstructionReviewTarget(
            target_type=target_type,
            name=name,
            source_ref=source_ref,
        )
        metadata = {
            "allowed_tools": allowed_tools or [],
            "has_allowed_tools": allowed_tools is not None,
            "always": False,
            "actions": [],
            "references": [],
            "scripts": [],
            "max_tokens": None,
            "examples": None,
            "source_layer": "ad-hoc",
        }
        return self._build_report(target=target, text=prompt or "", metadata=metadata)

    def _build_report(
        self,
        *,
        target: InstructionReviewTarget,
        text: str,
        metadata: dict[str, Any],
    ) -> InstructionReviewReport:
        rubric = [
            self._review_trigger_clarity(text, target),
            self._review_activation_risk(text, metadata),
            self._review_context_loading(text, metadata),
            self._review_tool_policy(text, metadata),
            self._review_safety_boundaries(text),
            self._review_examples_quality(text, metadata),
            self._review_yue_runtime_fit(text, target),
        ]
        blockers = [finding for item in rubric if item.status == "blocker" for finding in item.findings]
        recommendations = [
            finding
            for item in rubric
            if item.status != "blocker"
            for finding in item.findings
        ]
        if blockers:
            overall_status: InstructionReviewStatus = "blocker"
            summary = "Instruction review found blockers that should be resolved before activation."
        elif recommendations:
            overall_status = "warning"
            summary = "Instruction review found recommendations; activation can remain an explicit admin decision."
        else:
            overall_status = "pass"
            summary = "Instruction review found no blockers or recommendations for this runtime slice."
        return InstructionReviewReport(
            target=target,
            review_scope=list(self.REVIEW_SCOPE),
            summary=summary,
            overall_status=overall_status,
            rubric=rubric,
            blockers=blockers,
            recommendations=recommendations,
        )

    def _review_trigger_clarity(self, text: str, target: InstructionReviewTarget) -> InstructionReviewRubricItem:
        lower = text.lower()
        findings = []
        has_trigger_language = any(
            phrase in lower
            for phrase in (
                "use when",
                "always use",
                "trigger",
                "select this",
                "invoke",
                "when the user",
                "entry point",
            )
        )
        if not has_trigger_language:
            findings.append(
                self._finding(
                    "trigger_missing",
                    "Trigger guidance is unclear",
                    f"{target.target_type.title()} instructions do not describe when the runtime should select it.",
                    "Add concise trigger language that distinguishes this capability from adjacent modes or agents.",
                )
            )
            return self._rubric("trigger_clarity", "Trigger clarity", "warning", findings)
        if self._contains_any(lower, ("always use", "for any task", "all requests", "every request")):
            findings.append(
                self._finding(
                    "trigger_too_broad",
                    "Trigger may over-activate",
                    "Trigger language appears broad enough to capture unrelated work.",
                    "Narrow the trigger to specific user intents and name non-trigger cases.",
                )
            )
            return self._rubric("trigger_clarity", "Trigger clarity", "warning", findings)
        return self._rubric("trigger_clarity", "Trigger clarity", "pass", findings)

    def _review_activation_risk(self, text: str, metadata: dict[str, Any]) -> InstructionReviewRubricItem:
        lower = text.lower()
        findings = []
        if metadata.get("always"):
            findings.append(
                self._finding(
                    "automatic_activation",
                    "Automatic activation needs admin review",
                    "The target is configured or described as automatic, which raises routing blast radius.",
                    "Keep activation manual until trigger and tool boundaries are verified in Skill Health or import preview.",
                )
            )
        if self._contains_any(lower, ("ignore previous instructions", "override system", "bypass", "disable safety")):
            findings.append(
                self._finding(
                    "instruction_override_risk",
                    "Instruction override language detected",
                    "The prompt includes language that can conflict with Yue's host and safety boundaries.",
                    "Remove override language or rewrite it as scoped task guidance subordinate to host policy.",
                )
            )
            return self._rubric("activation_risk", "Activation risk", "blocker", findings)
        return self._rubric("activation_risk", "Activation risk", "warning" if findings else "pass", findings)

    def _review_context_loading(self, text: str, metadata: dict[str, Any]) -> InstructionReviewRubricItem:
        findings = []
        token_hint = max(1, len(text) // 4)
        if token_hint > 6000:
            findings.append(
                self._finding(
                    "context_load_large",
                    "Instruction context is large",
                    "The instruction body is large enough to create avoidable prompt load.",
                    "Move supporting material into references and keep default runtime instructions concise.",
                )
            )
        if metadata.get("max_tokens") and metadata["max_tokens"] > 16000:
            findings.append(
                self._finding(
                    "max_tokens_high",
                    "Context budget is high",
                    "The declared max token budget is high for a runtime-selected capability.",
                    "Lower the default budget or require explicit deep-work mode before loading large context.",
                )
            )
        return self._rubric("context_loading", "Context loading", "warning" if findings else "pass", findings)

    def _review_tool_policy(self, text: str, metadata: dict[str, Any]) -> InstructionReviewRubricItem:
        lower = text.lower()
        findings = []
        destructive_terms = ("delete", "remove files", "overwrite", "shell", "terminal", "exec", "network", "publish")
        mentions_tools = self._contains_any(lower, destructive_terms)
        if mentions_tools and not metadata.get("has_allowed_tools"):
            findings.append(
                self._finding(
                    "tool_policy_missing",
                    "Tool policy is not explicit",
                    "Instructions mention operational tools or side effects without an explicit allowed-tools boundary.",
                    "Declare allowed tools and approval expectations in the skill or agent configuration.",
                )
            )
            return self._rubric("tool_policy", "Tool policy", "blocker", findings)
        if any(tool in {"*", "all"} for tool in metadata.get("allowed_tools", [])):
            findings.append(
                self._finding(
                    "tool_policy_too_broad",
                    "Tool policy is too broad",
                    "Allowed tools are effectively unrestricted.",
                    "Replace wildcard access with the smallest runtime tool set needed for the capability.",
                )
            )
            return self._rubric("tool_policy", "Tool policy", "blocker", findings)
        if not metadata.get("has_allowed_tools"):
            findings.append(
                self._finding(
                    "tool_policy_unspecified",
                    "Tool policy is unspecified",
                    "No explicit allowed-tools boundary is available for display in the admin report.",
                    "Add an explicit empty allowed-tools list for prompt-only targets or list the permitted tools.",
                )
            )
        return self._rubric("tool_policy", "Tool policy", "warning" if findings else "pass", findings)

    def _review_safety_boundaries(self, text: str) -> InstructionReviewRubricItem:
        lower = text.lower()
        findings = []
        if self._contains_any(lower, ("without asking", "no approval", "do not ask permission", "auto-approve")):
            findings.append(
                self._finding(
                    "approval_boundary_missing",
                    "Approval boundary is risky",
                    "Instructions discourage explicit approval for potentially consequential actions.",
                    "Require preview and approval before external side effects, destructive edits, publishing, or activation.",
                )
            )
            return self._rubric("safety_boundaries", "Safety boundaries", "blocker", findings)
        if not self._contains_any(lower, ("approval", "safe", "boundary", "ask", "confirm", "preview")):
            findings.append(
                self._finding(
                    "safety_boundary_unspecified",
                    "Safety boundary is implicit",
                    "Instructions do not state how the runtime should handle risky actions or approvals.",
                    "Add a short safety section covering approvals, destructive actions, secrets, and external side effects.",
                )
            )
        return self._rubric("safety_boundaries", "Safety boundaries", "warning" if findings else "pass", findings)

    def _review_examples_quality(self, text: str, metadata: dict[str, Any]) -> InstructionReviewRubricItem:
        lower = text.lower()
        findings = []
        has_examples = bool(metadata.get("examples")) or self._contains_any(lower, ("example:", "examples", "user:", "assistant:"))
        if not has_examples:
            findings.append(
                self._finding(
                    "examples_missing",
                    "Examples are missing",
                    "No example usage is available to calibrate runtime behavior.",
                    "Add one positive example and one near-miss example that should not activate this capability.",
                )
            )
        return self._rubric("examples_quality", "Examples quality", "warning" if findings else "pass", findings)

    def _review_yue_runtime_fit(self, text: str, target: InstructionReviewTarget) -> InstructionReviewRubricItem:
        lower = text.lower()
        findings = []
        if self._contains_any(lower, ("marketplace publish", "publish to marketplace", "full ide", "authoring ide")):
            findings.append(
                self._finding(
                    "authoring_ide_scope",
                    "Scope drifts into authoring IDE",
                    "Instructions suggest marketplace publishing or full authoring workflows beyond Yue's runtime/workbench role.",
                    "Frame the target as a runtime capability with admin review, activation, and workbench artifacts.",
                )
            )
            return self._rubric("yue_runtime_fit", "Yue runtime fit", "blocker", findings)
        if target.target_type == "skill" and not self._contains_any(lower, ("artifact", "runtime", "workbench", "skill", "mode")):
            findings.append(
                self._finding(
                    "runtime_fit_unspecified",
                    "Runtime fit is not explicit",
                    "Instructions do not clearly describe the Yue runtime or workbench artifact role.",
                    "State how the capability behaves inside Yue's trusted workbench and what artifact or report it returns.",
                )
            )
        return self._rubric("yue_runtime_fit", "Yue runtime fit", "warning" if findings else "pass", findings)

    @staticmethod
    def _join_text(*parts: Optional[str]) -> str:
        return "\n\n".join(part.strip() for part in parts if part and part.strip())

    @staticmethod
    def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

    @staticmethod
    def _finding(code: str, title: str, detail: str, recommendation: str) -> InstructionReviewFinding:
        return InstructionReviewFinding(
            code=code,
            title=title,
            detail=detail,
            recommendation=recommendation,
        )

    @staticmethod
    def _rubric(
        key: str,
        label: str,
        status: InstructionReviewStatus,
        findings: list[InstructionReviewFinding],
    ) -> InstructionReviewRubricItem:
        return InstructionReviewRubricItem(
            key=key,
            label=label,
            status=status,
            findings=findings,
        )
