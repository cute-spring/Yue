from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.services.skills.compatibility import SkillCompatibilityEvaluator
from app.services.skills.import_models import (
    SkillImportLifecycleState,
    SkillImportPreview,
    SkillImportRecord,
    SkillImportReport,
    SkillImportResult,
    SkillImportSourceType,
    SkillImportStoredEntry,
    SkillPreviewAction,
    SkillPreviewOverlay,
    SkillPreviewResource,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.parsing import SkillLoader


class SkillImportService:
    def __init__(
        self,
        *,
        import_store: Optional[SkillImportStore] = None,
        compatibility_evaluator: Optional[SkillCompatibilityEvaluator] = None,
        agent_store: Optional[object] = None,
    ):
        self.import_store = import_store or SkillImportStore()
        self.compatibility_evaluator = compatibility_evaluator or SkillCompatibilityEvaluator()
        self.agent_store = agent_store

    def import_from_directory(
        self,
        package_dir: str | Path,
        *,
        source_type: SkillImportSourceType = SkillImportSourceType.DIRECTORY,
        source_ref: Optional[str] = None,
        auto_activate: bool = False,
        auto_mount_to_default_agent: bool = False,
        default_agent_id: Optional[str] = None,
    ) -> SkillImportResult:
        package_path = Path(package_dir).expanduser().resolve()
        display_source_ref = source_ref or str(package_path)

        package = SkillLoader.parse_package(package_path)
        if not package:
            record = SkillImportRecord(
                skill_name=package_path.name,
                skill_version="unknown",
                display_name=package_path.name,
                source_type=source_type,
                source_ref=display_source_ref,
                package_format="unknown",
                lifecycle_state=SkillImportLifecycleState.REJECTED,
                reason_code="parse_failed",
            )
            result = SkillImportResult(
                record=record,
                report=SkillImportReport(
                    import_id=record.id,
                    parse_status="failed",
                    standard_validation_status="failed",
                    compatibility_status="unknown",
                    activation_eligibility="ineligible",
                    errors=[f"Failed to parse skill package: {package_path}"],
                ),
                preview=SkillImportPreview(
                    skill_name=package_path.name,
                    skill_version="unknown",
                    description="",
                    capabilities=[],
                    entrypoint="",
                ),
            )
            self.import_store.save_entry(SkillImportStoredEntry(**result.model_dump()))
            return result

        validation = SkillLoader.validate_package(package)
        preview = self._build_preview(package)
        lifecycle_state = SkillImportLifecycleState.REJECTED
        reason_code = "validation_failed"
        compatibility_status = "unknown"
        activation_eligibility = "ineligible"
        compatibility_issues = []
        errors = list(validation.errors)
        warnings = list(validation.warnings)
        compat_generated = bool((package.metadata or {}).get("compat_generated"))
        compat_protocol = (package.metadata or {}).get("compat_protocol")
        compat_auto_filled_fields = list((package.metadata or {}).get("compat_missing_fields") or [])
        if compat_generated and compat_auto_filled_fields:
            warnings.append(
                "Compatibility mode auto-filled fields: " + ", ".join(compat_auto_filled_fields)
            )
        default_agent_mount_status = "not_attempted"

        if validation.is_valid:
            compatibility = self.compatibility_evaluator.evaluate_package(package)
            compatibility_status = compatibility.status
            compatibility_issues = list(compatibility.issues)
            if compatibility.status == "compatible":
                activation_eligibility = "eligible"
                if auto_activate and not self._has_active_import(package.name):
                    lifecycle_state = SkillImportLifecycleState.ACTIVE
                    reason_code = "auto_activated"
                else:
                    lifecycle_state = SkillImportLifecycleState.INACTIVE
                    reason_code = "manual_activation_required" if not auto_activate else "active_version_exists"
            else:
                lifecycle_state = SkillImportLifecycleState.REJECTED
                reason_code = "compatibility_failed"

        if auto_mount_to_default_agent and lifecycle_state == SkillImportLifecycleState.ACTIVE:
            target_agent = default_agent_id or os.getenv("YUE_SKILL_IMPORT_DEFAULT_AGENT_ID", "builtin-action-lab")
            default_agent_mount_status = self._mount_skill_to_agent(
                target_agent_id=target_agent,
                skill_ref=f"{package.name}:{package.version}",
            )
        elif auto_mount_to_default_agent:
            default_agent_mount_status = "skipped_not_active"

        record = SkillImportRecord(
            skill_name=package.name,
            skill_version=package.version,
            display_name=package.name,
            source_type=source_type,
            source_ref=display_source_ref,
            package_format=package.package_format,
            lifecycle_state=lifecycle_state,
            reason_code=reason_code,
        )
        report = SkillImportReport(
            import_id=record.id,
            parse_status="passed",
            standard_validation_status="passed" if validation.is_valid else "failed",
            compatibility_status=compatibility_status,
            activation_eligibility=activation_eligibility,
            errors=errors,
            warnings=warnings,
            compatibility_issues=compatibility_issues,
            compat_generated=compat_generated,
            compat_protocol=compat_protocol,
            compat_auto_filled_fields=compat_auto_filled_fields,
            default_agent_mount_status=default_agent_mount_status,
        )
        result = SkillImportResult(record=record, report=report, preview=preview)
        self.import_store.save_entry(SkillImportStoredEntry(**result.model_dump()))
        return result

    def _mount_skill_to_agent(self, *, target_agent_id: str, skill_ref: str) -> str:
        if self.agent_store is None:
            return "agent_store_unavailable"
        agent = self.agent_store.get_agent(target_agent_id)
        if not agent:
            return "agent_not_found"
        visible_skills = list(getattr(agent, "visible_skills", []) or [])
        if skill_ref in visible_skills:
            return "already_mounted"
        visible_skills.append(skill_ref)
        self.agent_store.update_agent(target_agent_id, {"visible_skills": visible_skills})
        return "mounted"

    def _has_active_import(self, skill_name: str) -> bool:
        for entry in self.import_store.list_entries():
            record = entry.record
            if record.skill_name != skill_name:
                continue
            if record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
                continue
            return True
        return False

    def _build_preview(self, package) -> SkillImportPreview:
        required_tools = sorted({action.tool for action in package.actions if action.tool})
        requires = package.requires or {}
        return SkillImportPreview(
            skill_name=package.name,
            skill_version=package.version,
            description=package.description,
            capabilities=list(package.capabilities or []),
            entrypoint=package.entrypoint,
            required_tools=required_tools,
            requires_bins=list(requires.get("bins") or []),
            requires_env=list(requires.get("env") or []),
            resources=[
                SkillPreviewResource(id=item.id, path=item.path, kind=item.kind)
                for item in package.resources
            ],
            actions=[
                SkillPreviewAction(
                    id=item.id,
                    tool=item.tool,
                    path=item.path,
                    runtime=item.runtime,
                    approval_policy=item.approval_policy,
                )
                for item in package.actions
            ],
            overlays=[
                SkillPreviewOverlay(provider=item.provider, model=item.model, path=item.path)
                for item in package.overlays
            ],
            always=package.always,
        )
