from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.agent_store import DEFAULT_SKILL_PLAYGROUND_AGENT_ID
from app.services.skill_service import get_stage4_lite_runtime_context
from app.services.skills.bootstrap import resolve_skill_runtime_config_from_env
from app.services.skills.directories import SkillDirectoryResolver
from app.services.skills.preflight_service import SkillPreflightService
from app.services.skills.setup_service import SkillSetupService

router = APIRouter()
EXCALIDRAW_SKILL_NAME = "excalidraw-diagram-generator"


class SkillPreflightMountRequest(BaseModel):
    agent_id: Optional[str] = None


class SkillPreflightSetupRequest(BaseModel):
    pass


def _runtime_context():
    return get_stage4_lite_runtime_context()


def _runtime_store():
    return _runtime_context().skill_import_store


def _resolve_preflight_directories():
    config = resolve_skill_runtime_config_from_env()
    return SkillDirectoryResolver(
        builtin_dir=config.builtin_skills_dir,
        workspace_dir=config.workspace_skills_dir,
        user_dir=config.user_skills_dir,
    ).resolve()


def _default_agent_visible_skill_refs() -> set[str]:
    runtime_service = _runtime_context().skill_import_service
    if runtime_service is None or runtime_service.agent_store is None:
        return set()
    agent = runtime_service.agent_store.get_agent(DEFAULT_SKILL_PLAYGROUND_AGENT_ID)
    if agent is None:
        return set()
    return set(getattr(agent, "visible_skills", []) or [])


def _status_message_and_next_action(status: str, issues: list[str]) -> tuple[str, str]:
    if status == "available":
        return "Ready to mount.", "Mount this skill to Skill Playground."
    if status == "needs_fix":
        message = issues[0] if issues else "Preflight checks found issues."
        return message, "Resolve listed issues, then rerun preflight."
    return "Skill is unavailable.", "Check compatibility and required dependencies."


def _serialize_preflight_item(item, visible_skill_refs: set[str]) -> dict:
    data = item.model_dump(mode="json")
    status_message, next_action = _status_message_and_next_action(
        status=data.get("status", ""),
        issues=data.get("issues", []),
    )
    data["mountable"] = data.get("status") == "available"
    data["visible_in_default_agent"] = data.get("skill_ref") in visible_skill_refs
    data["status_message"] = status_message
    data["next_action"] = next_action
    setup_capable = bool(data.get("setup_capable"))
    trust_status = data.get("trust_status") or "untrusted"
    setup_status = data.get("setup_status") or "not_needed"
    data["setup_required"] = bool(setup_capable and setup_status != "succeeded")
    if not setup_capable:
        data["setup_status_message"] = "No trusted setup contract declared."
        data["setup_next_action"] = "Use Mount if preflight is available."
    elif trust_status != "trusted":
        data["setup_status_message"] = "Setup requires explicit trust."
        data["setup_next_action"] = "Trust this skill, then run setup."
    elif setup_status == "succeeded":
        data["setup_status_message"] = "Trusted setup completed."
        data["setup_next_action"] = "Setup is complete."
    elif setup_status == "failed":
        data["setup_status_message"] = data.get("setup_last_error") or "Trusted setup failed."
        data["setup_next_action"] = "Fix setup issues, then rerun setup."
    else:
        data["setup_status_message"] = "Ready to run trusted setup."
        data["setup_next_action"] = "Run setup in isolated environment."
    audit_entries = data.get("setup_audit_entries") or []
    data["setup_audit_summary"] = {
        "total": len(audit_entries),
        "succeeded": sum(1 for e in audit_entries if e.get("exit_code") == 0),
        "failed": sum(1 for e in audit_entries if e.get("exit_code") != 0),
        "total_duration_ms": sum(e.get("duration_ms", 0) for e in audit_entries),
    }
    if data.get("skill_name") == EXCALIDRAW_SKILL_NAME:
        data["excalidraw_health"] = _build_excalidraw_health(data)
    return data


def _build_excalidraw_health(data: dict) -> dict:
    issues = [str(item) for item in (data.get("issues") or [])]
    lower_issues = [item.lower() for item in issues]
    unsupported_tools = list(data.get("unsupported_tools") or [])
    missing_bins = list(data.get("missing_bins") or [])
    missing_env = list(data.get("missing_env") or [])
    source_path = str(data.get("source_path") or "").strip()

    icon_library_available = not any(
        ("excalidraw" in item and "librar" in item) or "icons/" in item for item in lower_issues
    )
    script_dependencies_ready = not missing_bins and not missing_env and not any(
        "missing required binary" in item for item in lower_issues
    )
    action_invocable = data.get("status") != "unavailable" and not unsupported_tools
    auto_enhance_ready = action_invocable and script_dependencies_ready and icon_library_available and data.get("status") == "available"

    if auto_enhance_ready:
        effective_level = "L3"
    elif action_invocable and script_dependencies_ready and icon_library_available:
        effective_level = "L2"
    elif action_invocable and script_dependencies_ready:
        effective_level = "L1"
    else:
        effective_level = "L0"

    blockers = []
    split_command = None
    if source_path:
        split_command = f"python {source_path}/scripts/split-excalidraw-library.py {source_path}/libraries/<icon-set>/"
    if not icon_library_available:
        blockers.append(
            {
                "code": "icon_library_missing",
                "title": "Excalidraw icon library missing",
                "detail": "Icon set assets are not ready, so L2/L3 capabilities are blocked.",
                "fix_command": split_command,
                "fix_path": f"{source_path}/libraries" if source_path else None,
            }
        )
    if not script_dependencies_ready:
        blockers.append(
            {
                "code": "script_dependency_missing",
                "title": "Script dependency missing",
                "detail": "Runtime dependencies are missing for Excalidraw actions.",
                "fix_command": split_command,
                "fix_path": f"{source_path}/scripts" if source_path else None,
            }
        )
    if not action_invocable:
        blockers.append(
            {
                "code": "action_not_invocable",
                "title": "Action invocation unavailable",
                "detail": "Action tooling or package compatibility prevents invocation.",
                "fix_command": None,
                "fix_path": source_path or None,
            }
        )

    return {
        "effective_level": effective_level,
        "levels": ["L1", "L2", "L3"],
        "checks": {
            "icon_library_available": icon_library_available,
            "script_dependencies_ready": script_dependencies_ready,
            "action_invocable": action_invocable,
            "auto_enhance_ready": auto_enhance_ready,
        },
        "blockers": blockers,
    }


def _raise_actionable_error(*, status_code: int, code: str, message: str, next_action: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "next_action": next_action,
        },
    )


@router.post("/rescan")
async def rescan_skill_preflight():
    context = _runtime_context()
    compatibility_evaluator = getattr(
        getattr(context, "skill_import_service", None),
        "compatibility_evaluator",
        None,
    )
    service = SkillPreflightService(
        import_store=context.skill_import_store,
        compatibility_evaluator=compatibility_evaluator,
    )
    records = service.refresh(_resolve_preflight_directories())
    visible_skill_refs = _default_agent_visible_skill_refs()
    items = [_serialize_preflight_item(item, visible_skill_refs) for item in records]
    summary = {
        "total": len(items),
        "available": sum(1 for item in items if item.get("status") == "available"),
        "needs_fix": sum(1 for item in items if item.get("status") == "needs_fix"),
        "unavailable": sum(1 for item in items if item.get("status") == "unavailable"),
    }
    return {
        "summary": summary,
        "items": items,
    }


@router.get("/")
async def list_skill_preflight(
    status: Optional[str] = Query(default=None),
    skill_name: Optional[str] = Query(default=None),
    source_layer: Optional[str] = Query(default=None),
):
    records = _runtime_store().list_preflight_records()
    valid_status = {"available", "needs_fix", "unavailable"}
    if status and status not in valid_status:
        raise HTTPException(status_code=400, detail="invalid_request")

    if status:
        records = [item for item in records if item.status == status]
    if skill_name:
        records = [item for item in records if item.skill_name == skill_name]
    if source_layer:
        records = [item for item in records if item.source_layer == source_layer]

    records.sort(key=lambda item: item.checked_at, reverse=True)
    visible_skill_refs = _default_agent_visible_skill_refs()
    return {"items": [_serialize_preflight_item(item, visible_skill_refs) for item in records]}


@router.get("/{skill_ref}")
async def get_skill_preflight(skill_ref: str):
    item = _runtime_store().get_preflight_record(skill_ref)
    if item is None:
        raise HTTPException(status_code=404, detail="skill_preflight_not_found")
    visible_skill_refs = _default_agent_visible_skill_refs()
    return {"item": _serialize_preflight_item(item, visible_skill_refs)}


@router.get("/{skill_ref}/setup")
async def get_skill_preflight_setup(skill_ref: str):
    setup_service = SkillSetupService(import_store=_runtime_store())
    try:
        item = setup_service.get_setup_state(skill_ref)
    except KeyError:
        raise HTTPException(status_code=404, detail="skill_preflight_not_found")
    visible_skill_refs = _default_agent_visible_skill_refs()
    return {"item": _serialize_preflight_item(item, visible_skill_refs)}


@router.post("/{skill_ref}/trust")
async def trust_skill_preflight(skill_ref: str):
    setup_service = SkillSetupService(import_store=_runtime_store())
    try:
        item = setup_service.trust_skill(skill_ref)
    except KeyError:
        raise HTTPException(status_code=404, detail="skill_preflight_not_found")
    except ValueError:
        _raise_actionable_error(
            status_code=422,
            code="skill_setup_not_supported",
            message="Skill does not declare a Phase 1 install.setup contract.",
            next_action="Add manifest install.setup runtime and commands first.",
        )
    except RuntimeError:
        _raise_actionable_error(
            status_code=409,
            code="skill_setup_requires_rescan",
            message="Skill package changed since preflight.",
            next_action="Rescan preflight, then review and trust the current package.",
        )
    visible_skill_refs = _default_agent_visible_skill_refs()
    return {"item": _serialize_preflight_item(item, visible_skill_refs)}


@router.post("/{skill_ref}/setup")
async def setup_skill_preflight(skill_ref: str, request: SkillPreflightSetupRequest):
    del request
    setup_service = SkillSetupService(import_store=_runtime_store())
    try:
        item = setup_service.run_setup(skill_ref)
    except KeyError:
        raise HTTPException(status_code=404, detail="skill_preflight_not_found")
    except PermissionError:
        _raise_actionable_error(
            status_code=422,
            code="skill_setup_requires_trust",
            message="Skill must be trusted before setup can run.",
            next_action="Call trust endpoint first.",
        )
    except ValueError:
        _raise_actionable_error(
            status_code=422,
            code="skill_setup_not_supported",
            message="Skill setup is unavailable or manifest contract is invalid.",
            next_action="Verify install.setup runtime and commands in manifest.",
        )
    visible_skill_refs = _default_agent_visible_skill_refs()
    return {"item": _serialize_preflight_item(item, visible_skill_refs)}


@router.post("/{skill_ref}/mount")
async def mount_skill_preflight(skill_ref: str, request: SkillPreflightMountRequest):
    item = _runtime_store().get_preflight_record(skill_ref)
    if item is None:
        _raise_actionable_error(
            status_code=404,
            code="skill_preflight_not_found",
            message="Skill preflight record was not found.",
            next_action="Refresh preflight records and verify the skill reference.",
        )
    if item.status != "available":
        _raise_actionable_error(
            status_code=422,
            code="skill_preflight_not_mountable",
            message="Skill is not mountable until preflight issues are resolved.",
            next_action="Resolve listed issues, then rerun preflight.",
        )

    runtime_service = _runtime_context().skill_import_service
    if runtime_service is None:
        _raise_actionable_error(
            status_code=503,
            code="skill_import_service_unavailable",
            message="Skill import service is unavailable.",
            next_action="Check runtime bootstrap wiring and retry.",
        )

    target_agent_id = request.agent_id or DEFAULT_SKILL_PLAYGROUND_AGENT_ID
    mount_status = runtime_service._mount_skill_to_agent(
        target_agent_id=target_agent_id,
        skill_ref=skill_ref,
    )
    if mount_status == "agent_not_found":
        _raise_actionable_error(
            status_code=404,
            code="agent_not_found",
            message="Target agent was not found.",
            next_action="Use an existing agent id or create the target agent first.",
        )
    if mount_status == "agent_store_unavailable":
        _raise_actionable_error(
            status_code=503,
            code="agent_store_unavailable",
            message="Agent store is unavailable.",
            next_action="Verify host adapter agent store wiring and retry.",
        )
    if mount_status not in {"mounted", "already_mounted"}:
        _raise_actionable_error(
            status_code=500,
            code="skill_mount_unknown_error",
            message="Unknown error occurred while mounting skill.",
            next_action="Check backend logs and retry the operation.",
        )
    return {
        "skill_ref": skill_ref,
        "agent_id": target_agent_id,
        "mount_status": mount_status,
    }
