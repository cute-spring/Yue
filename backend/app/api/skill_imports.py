from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.skill_service import (
    get_stage4_lite_host_adapters,
    get_stage4_lite_runtime_context,
    refresh_skill_runtime_catalog,
)
from app.services.skills.import_models import (
    SkillImportReport,
    SkillImportLifecycleState,
    SkillImportSourceType,
    SkillImportStoredEntry,
)
from app.services.skills.runtime_catalog import is_skill_import_mutation_allowed

router = APIRouter()
_runtime_mutation_lock = threading.RLock()


class SkillImportCreateRequest(BaseModel):
    source_type: Optional[str] = None
    source_path: Optional[str] = None


class SkillImportActivateRequest(BaseModel):
    pass


class SkillImportReplaceRequest(BaseModel):
    target_skill_name: Optional[str] = None


def _runtime_context():
    return get_stage4_lite_runtime_context()


def _runtime_store():
    return _runtime_context().skill_import_store


def _runtime_service():
    return _runtime_context().skill_import_service


def _feature_flags() -> Dict[str, Any]:
    # Transitional compatibility helper: import APIs should read feature flags
    # through host adapters instead of exposing config-service shims.
    return dict(get_stage4_lite_host_adapters().feature_flag_provider.get_feature_flags() or {})


def _ensure_import_mutation_allowed() -> None:
    if is_skill_import_mutation_allowed():
        return
    raise HTTPException(status_code=409, detail="skill_import_mutation_unavailable_in_legacy_mode")


def _to_import_record_payload(entry: SkillImportStoredEntry) -> Dict[str, Any]:
    return entry.record.model_dump(mode="json")


def _not_found(import_id: str) -> None:
    raise HTTPException(status_code=404, detail="skill_import_not_found")


def _get_entry_or_404(import_id: str) -> SkillImportStoredEntry:
    entry = _runtime_store().get_entry(import_id)
    if entry is None:
        _not_found(import_id)
    return entry


def _save_entry(entry: SkillImportStoredEntry) -> SkillImportStoredEntry:
    entry.record.updated_at = datetime.utcnow()
    return _runtime_store().save_entry(entry)


def _resolve_import_failure_detail(report: SkillImportReport) -> str:
    if report.parse_status == "failed":
        return "skill_parse_failed"
    if report.standard_validation_status == "failed":
        return "skill_standard_validation_failed"
    if report.compatibility_status == "incompatible":
        return "skill_yue_compatibility_failed"
    return "skill_activation_ineligible"


def _should_auto_activate() -> bool:
    feature_flags = _feature_flags()
    return feature_flags.get("skill_import_auto_activate_enabled", True)

def _should_auto_mount_default_agent() -> bool:
    feature_flags = _feature_flags()
    return feature_flags.get("skill_import_default_agent_auto_mount_enabled", False)


def _build_import_response(result):
    payload = {
        "import": result.record.model_dump(mode="json"),
        "report": result.report.model_dump(mode="json"),
        "preview": result.preview.model_dump(mode="json"),
    }
    if result.record.lifecycle_state == SkillImportLifecycleState.ACTIVE:
        refresh_skill_runtime_catalog()
    return payload


@router.post("/", status_code=201)
async def create_skill_import(request: SkillImportCreateRequest):
    _ensure_import_mutation_allowed()
    if request.source_type and request.source_type != SkillImportSourceType.DIRECTORY.value:
        raise HTTPException(status_code=400, detail="invalid_request")
    if not request.source_path:
        raise HTTPException(status_code=400, detail="import_source_missing")
    package_dir = Path(request.source_path).expanduser()
    if not package_dir.exists():
        raise HTTPException(status_code=404, detail="import_source_not_found")

    with _runtime_mutation_lock:
        result = _runtime_service().import_from_directory(
            package_dir,
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(package_dir),
            auto_activate=_should_auto_activate(),
            auto_mount_to_default_agent=_should_auto_mount_default_agent(),
        )
    status_code = 201 if result.report.activation_eligibility == "eligible" else 422
    payload = _build_import_response(result)
    if status_code == 422:
        detail_code = _resolve_import_failure_detail(result.report)
        return JSONResponse(
            status_code=422,
            content={
                "detail": detail_code,
                "report": payload["report"],
                "import": payload["import"],
                "preview": payload["preview"],
            },
        )
    return payload


@router.get("/")
async def list_skill_imports(
    skill_name: Optional[str] = Query(default=None),
    lifecycle_state: Optional[str] = Query(default=None),
    latest_only: bool = Query(default=False),
):
    entries = _runtime_store().list_entries()
    valid_lifecycle_states = {state.value for state in SkillImportLifecycleState}

    if lifecycle_state and lifecycle_state not in valid_lifecycle_states:
        raise HTTPException(status_code=400, detail="invalid_request")

    if skill_name:
        entries = [item for item in entries if item.record.skill_name == skill_name]
    if lifecycle_state:
        entries = [item for item in entries if item.record.lifecycle_state.value == lifecycle_state]

    if latest_only:
        latest_by_skill: Dict[str, SkillImportStoredEntry] = {}
        for entry in entries:
            previous = latest_by_skill.get(entry.record.skill_name)
            if previous is None or entry.record.updated_at > previous.record.updated_at:
                latest_by_skill[entry.record.skill_name] = entry
        entries = list(latest_by_skill.values())

    entries.sort(key=lambda item: item.record.updated_at, reverse=True)
    return {"items": [_to_import_record_payload(item) for item in entries]}


@router.get("/{import_id}")
async def get_skill_import(import_id: str):
    entry = _get_entry_or_404(import_id)
    return {
        "import": entry.record.model_dump(mode="json"),
        "report": entry.report.model_dump(mode="json"),
        "preview": entry.preview.model_dump(mode="json"),
    }


@router.post("/{import_id}/activate")
async def activate_skill_import(import_id: str, _: SkillImportActivateRequest):
    _ensure_import_mutation_allowed()
    with _runtime_mutation_lock:
        entry = _get_entry_or_404(import_id)

        if entry.record.lifecycle_state == SkillImportLifecycleState.ACTIVE:
            raise HTTPException(status_code=409, detail="skill_import_already_active")

        if entry.record.lifecycle_state != SkillImportLifecycleState.INACTIVE:
            raise HTTPException(status_code=422, detail="skill_activation_ineligible")
        if entry.report.activation_eligibility != "eligible":
            raise HTTPException(status_code=422, detail="skill_activation_ineligible")

        for candidate in _runtime_store().list_entries():
            if (
                candidate.record.id != import_id
                and candidate.record.skill_name == entry.record.skill_name
                and candidate.record.lifecycle_state == SkillImportLifecycleState.ACTIVE
            ):
                raise HTTPException(status_code=409, detail="skill_replacement_conflict")

        entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
        entry.record.reason_code = "activated_by_admin"
        _save_entry(entry)
        refresh_skill_runtime_catalog()

    return {
        "import_id": entry.record.id,
        "skill_name": entry.record.skill_name,
        "skill_version": entry.record.skill_version,
        "lifecycle_state": entry.record.lifecycle_state.value,
    }


@router.post("/{import_id}/deactivate")
async def deactivate_skill_import(import_id: str, _: SkillImportActivateRequest):
    _ensure_import_mutation_allowed()
    with _runtime_mutation_lock:
        entry = _get_entry_or_404(import_id)

        if entry.record.lifecycle_state != SkillImportLifecycleState.ACTIVE:
            raise HTTPException(status_code=409, detail="skill_import_not_active")

        entry.record.lifecycle_state = SkillImportLifecycleState.INACTIVE
        entry.record.reason_code = "deactivated_by_admin"
        _save_entry(entry)
        refresh_skill_runtime_catalog()

    return {
        "import_id": entry.record.id,
        "skill_name": entry.record.skill_name,
        "skill_version": entry.record.skill_version,
        "lifecycle_state": entry.record.lifecycle_state.value,
    }


@router.post("/{import_id}/replace")
async def replace_skill_import(import_id: str, request: SkillImportReplaceRequest):
    _ensure_import_mutation_allowed()
    with _runtime_mutation_lock:
        if not request.target_skill_name:
            raise HTTPException(status_code=400, detail="invalid_request")

        entry = _get_entry_or_404(import_id)

        if entry.record.lifecycle_state == SkillImportLifecycleState.ACTIVE:
            raise HTTPException(status_code=409, detail="skill_import_already_active")
        if entry.record.lifecycle_state != SkillImportLifecycleState.INACTIVE:
            raise HTTPException(status_code=422, detail="skill_activation_ineligible")
        if entry.report.activation_eligibility != "eligible":
            raise HTTPException(status_code=422, detail="skill_activation_ineligible")
        if entry.record.skill_name != request.target_skill_name:
            raise HTTPException(status_code=400, detail="invalid_request")

        active_entries = [
            item
            for item in _runtime_store().list_entries()
            if item.record.skill_name == request.target_skill_name
            and item.record.lifecycle_state == SkillImportLifecycleState.ACTIVE
        ]
        if len(active_entries) != 1:
            raise HTTPException(status_code=409, detail="skill_replacement_conflict")

        superseded_entry = active_entries[0]
        superseded_entry.record.lifecycle_state = SkillImportLifecycleState.SUPERSEDED
        superseded_entry.record.reason_code = "superseded_by_replacement"
        superseded_entry.record.superseded_by_import_id = entry.record.id

        entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
        entry.record.reason_code = "activated_by_replacement"
        entry.record.supersedes_import_id = superseded_entry.record.id

        _save_entry(superseded_entry)
        _save_entry(entry)
        refresh_skill_runtime_catalog()

    return {
        "activated_import_id": entry.record.id,
        "superseded_import_id": superseded_entry.record.id,
        "skill_name": entry.record.skill_name,
        "active_version": entry.record.skill_version,
    }
