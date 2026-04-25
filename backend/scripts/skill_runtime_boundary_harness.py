from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from app.services.skills.import_models import (
    SkillImportLifecycleState,
    SkillImportPreview,
    SkillImportRecord,
    SkillImportReport,
    SkillImportSourceType,
    SkillImportStoredEntry,
)
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillConstraints, SkillSpec
from app.services.skills.registry import SkillRegistry
from app.services.skills.routing import SkillRouter
from app.services.skills.runtime_seams import build_skill_runtime_seams


def _build_externalization_manifest(
    *,
    workspace_root: Path,
    status: str,
    checks: dict[str, bool],
    activation_refs: list[str],
    projected_dirs: list[str],
    visible_refs: list[str],
    effective_tools: list[str],
) -> dict:
    boundary_ids = sorted(checks.keys())
    boundary_evidence = {
        "activation_state_store": {"activation_refs": sorted(activation_refs)},
        "runtime_catalog_projector": {"projected_dirs": sorted(projected_dirs)},
        "visibility_resolver": {"visible_refs": sorted(visible_refs)},
        "tool_capability_provider": {"effective_tools": sorted(effective_tools)},
        "prompt_injection_adapter": {"prompt_injection_ready": checks["prompt_injection_adapter"]},
    }
    boundaries = [
        {
            "id": boundary_id,
            "status": "pass" if checks[boundary_id] else "fail",
            "deterministic_evidence": boundary_evidence.get(boundary_id, {}),
        }
        for boundary_id in boundary_ids
    ]
    return {
        "schema_version": "stage5-lite-boundary-manifest/v1",
        "stage": "stage5-lite",
        "mode": "non-publishing",
        "harness": "stage5-lite-runtime-boundary",
        "status": status,
        "workspace_root": str(workspace_root.resolve()),
        "boundary_ids": boundary_ids,
        "boundaries": boundaries,
    }


def _entry(
    *,
    skill_name: str,
    source_ref: str,
    lifecycle_state: SkillImportLifecycleState,
    source_type: SkillImportSourceType = SkillImportSourceType.DIRECTORY,
) -> SkillImportStoredEntry:
    record = SkillImportRecord(
        skill_name=skill_name,
        skill_version="1.0.0",
        display_name=skill_name,
        source_type=source_type,
        source_ref=source_ref,
        package_format="package_directory",
        lifecycle_state=lifecycle_state,
        updated_at=datetime.utcnow(),
    )
    return SkillImportStoredEntry(
        record=record,
        report=SkillImportReport(
            import_id=record.id,
            parse_status="passed",
            standard_validation_status="passed",
            compatibility_status="compatible",
            activation_eligibility="eligible",
        ),
        preview=SkillImportPreview(
            skill_name=skill_name,
            skill_version="1.0.0",
            description="harness",
            capabilities=["analysis"],
            entrypoint="system_prompt",
        ),
    )


def _write_skill_package(root: Path, name: str) -> Path:
    package_dir = root / name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "SKILL.md").write_text(
        f"""---
name: {name}
version: 1.0.0
description: boundary harness skill
capabilities: ["analysis"]
entrypoint: system_prompt
---
## System Prompt
You are a boundary harness skill.
""",
        encoding="utf-8",
    )
    return package_dir


def run_harness(*, workspace_root: Path, manifest_out: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="skill-runtime-boundary-") as td:
        temp_root = Path(td)
        package_root = temp_root / "packages"
        active_dir = _write_skill_package(package_root, "active-skill")
        _write_skill_package(package_root, "inactive-skill")

        store = SkillImportStore(data_dir=str(temp_root / "data"))
        store.save_entry(
            _entry(
                skill_name="active-skill",
                source_ref=str(active_dir),
                lifecycle_state=SkillImportLifecycleState.ACTIVE,
            )
        )
        store.save_entry(
            _entry(
                skill_name="inactive-skill",
                source_ref=str(package_root / "inactive-skill"),
                lifecycle_state=SkillImportLifecycleState.INACTIVE,
            )
        )

        registry = SkillRegistry()
        registry.register(
            SkillSpec(
                name="active-skill",
                version="1.0.0",
                description="active harness skill",
                capabilities=["analysis"],
                entrypoint="system_prompt",
                constraints=SkillConstraints(allowed_tools=["builtin:docs_read"]),
            )
        )
        router = SkillRouter(registry)
        seams = build_skill_runtime_seams(import_store=store, router=router)
        agent = SimpleNamespace(
            resolved_visible_skills=[],
            skill_groups=[],
            extra_visible_skills=[],
            visible_skills=["active-skill:1.0.0"],
        )

        activation_refs = seams.activation_state_store.list_active_source_refs()
        projected_dirs = seams.runtime_catalog_projector.project_active_import_dirs()
        visible_refs = seams.visibility_resolver.resolve_visible_skill_refs(agent)
        effective_tools = seams.tool_capability_provider.resolve_effective_tools(
            agent_tools=["builtin:docs_read", "builtin:exec_command"],
            skill=registry.get_skill("active-skill", "1.0.0"),
        )
        composed_prompt = seams.prompt_injection_adapter.compose_prompt(
            base_prompt="Base prompt",
            skill_prompt="[Active Skill: active-skill]\nSkill prompt",
        )

        checks = {
            "activation_state_store": activation_refs == [str(active_dir)],
            "runtime_catalog_projector": [item.path for item in projected_dirs] == [str(active_dir.resolve())],
            "visibility_resolver": visible_refs == ["active-skill:1.0.0"],
            "tool_capability_provider": effective_tools == ["builtin:docs_read"],
            "prompt_injection_adapter": composed_prompt.startswith("Base prompt\n\n[Active Skill: active-skill]"),
        }
        passed = all(checks.values())
        status = "pass" if passed else "fail"
        externalization_manifest = _build_externalization_manifest(
            workspace_root=workspace_root,
            status=status,
            checks=checks,
            activation_refs=activation_refs,
            projected_dirs=[item.path for item in projected_dirs],
            visible_refs=visible_refs,
            effective_tools=effective_tools,
        )
        if manifest_out is not None:
            manifest_out.parent.mkdir(parents=True, exist_ok=True)
            manifest_out.write_text(
                json.dumps(externalization_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return {
            "status": status,
            "workspace_root": str(workspace_root.resolve()),
            "harness": "stage5-lite-runtime-boundary",
            "checks": checks,
            "artifacts": {
                "activation_refs": activation_refs,
                "projected_dirs": [item.path for item in projected_dirs],
                "visible_refs": visible_refs,
                "effective_tools": effective_tools,
                "composed_prompt": composed_prompt,
                "externalization_manifest": externalization_manifest,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--manifest-out", default="")
    args = parser.parse_args()

    manifest_out = Path(args.manifest_out) if args.manifest_out else None
    report = run_harness(workspace_root=Path(args.workspace_root), manifest_out=manifest_out)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
