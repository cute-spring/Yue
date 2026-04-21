from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.skill_service import skill_import_service, skill_import_store
from app.services.skills.import_models import (
    SkillImportReport,
    SkillActivationStatus,
    SkillImportLifecycleState,
    SkillImportSourceType,
    SkillImportStoredEntry,
)

router = APIRouter()


class SkillImportCreateRequest(BaseModel):
    source_type: SkillImportSourceType
    source_path: Optional[str] = None
    upload_token: Optional[str] = None


class SkillImportActivateRequest(BaseModel):
    pass


class SkillImportReplaceRequest(BaseModel):
    target_skill_name: Optional[str] = None


def _to_import_record_payload(entry: SkillImportStoredEntry) -> Dict[str, Any]:
    return entry.record.model_dump(mode="json")


def _not_found(import_id: str) -> None:
    raise HTTPException(status_code=404, detail="skill_import_not_found")


def _get_entry_or_404(import_id: str) -> SkillImportStoredEntry:
    entry = skill_import_store.get_entry(import_id)
    if entry is None:
        _not_found(import_id)
    return entry


def _save_entry(entry: SkillImportStoredEntry) -> SkillImportStoredEntry:
    entry.record.updated_at = datetime.utcnow()
    return skill_import_store.save_entry(entry)


def _resolve_import_failure_detail(report: SkillImportReport) -> str:
    if report.parse_status == "failed":
        return "skill_parse_failed"
    if report.standard_validation_status == "failed":
        return "skill_standard_validation_failed"
    if report.compatibility_status == "incompatible":
        return "skill_yue_compatibility_failed"
    return "skill_activation_ineligible"


@router.post("/", status_code=201)
async def create_skill_import(request: SkillImportCreateRequest):
    if request.source_type == SkillImportSourceType.DIRECTORY:
        if not request.source_path:
            raise HTTPException(status_code=400, detail="import_source_missing")
        package_dir = Path(request.source_path).expanduser()
        if not package_dir.exists():
            raise HTTPException(status_code=404, detail="import_source_not_found")

        result = skill_import_service.import_from_directory(
            package_dir,
            source_type=SkillImportSourceType.DIRECTORY,
            source_ref=str(package_dir),
        )
        status_code = 201 if result.report.activation_eligibility == "eligible" else 422
        payload = {
            "import": result.record.model_dump(mode="json"),
            "report": result.report.model_dump(mode="json"),
            "preview": result.preview.model_dump(mode="json"),
        }
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

    if request.source_type == SkillImportSourceType.UPLOAD:
        if not request.upload_token:
            raise HTTPException(status_code=400, detail="import_source_missing")
        raise HTTPException(status_code=400, detail="import_unpack_failed")

    raise HTTPException(status_code=400, detail="invalid_request")


@router.get("/")
async def list_skill_imports(
    skill_name: Optional[str] = Query(default=None),
    lifecycle_state: Optional[str] = Query(default=None),
    activation_status: Optional[str] = Query(default=None),
    latest_only: bool = Query(default=False),
):
    entries = skill_import_store.list_entries()
    valid_lifecycle_states = {state.value for state in SkillImportLifecycleState}
    valid_activation_statuses = {status.value for status in SkillActivationStatus}

    if lifecycle_state and lifecycle_state not in valid_lifecycle_states:
        raise HTTPException(status_code=400, detail="invalid_request")
    if activation_status and activation_status not in valid_activation_statuses:
        raise HTTPException(status_code=400, detail="invalid_request")

    if skill_name:
        entries = [item for item in entries if item.record.skill_name == skill_name]
    if lifecycle_state:
        entries = [item for item in entries if item.record.lifecycle_state.value == lifecycle_state]
    if activation_status:
        entries = [item for item in entries if item.record.activation_status.value == activation_status]

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
    entry = _get_entry_or_404(import_id)

    if entry.record.activation_status == SkillActivationStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="skill_import_already_active")

    if entry.record.lifecycle_state != SkillImportLifecycleState.ACTIVATION_READY:
        raise HTTPException(status_code=422, detail="skill_activation_ineligible")

    for candidate in skill_import_store.list_entries():
        if (
            candidate.record.id != import_id
            and candidate.record.skill_name == entry.record.skill_name
            and candidate.record.activation_status == SkillActivationStatus.ACTIVE
        ):
            raise HTTPException(status_code=409, detail="skill_replacement_conflict")

    entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
    entry.record.activation_status = SkillActivationStatus.ACTIVE
    _save_entry(entry)

    return {
        "import_id": entry.record.id,
        "skill_name": entry.record.skill_name,
        "skill_version": entry.record.skill_version,
        "lifecycle_state": entry.record.lifecycle_state.value,
        "activation_status": entry.record.activation_status.value,
    }


@router.post("/{import_id}/deactivate")
async def deactivate_skill_import(import_id: str, _: SkillImportActivateRequest):
    entry = _get_entry_or_404(import_id)

    if entry.record.activation_status != SkillActivationStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="skill_import_not_active")

    entry.record.lifecycle_state = SkillImportLifecycleState.INACTIVE
    entry.record.activation_status = SkillActivationStatus.INACTIVE
    _save_entry(entry)

    return {
        "import_id": entry.record.id,
        "skill_name": entry.record.skill_name,
        "skill_version": entry.record.skill_version,
        "lifecycle_state": entry.record.lifecycle_state.value,
        "activation_status": entry.record.activation_status.value,
    }


@router.post("/{import_id}/replace")
async def replace_skill_import(import_id: str, request: SkillImportReplaceRequest):
    if not request.target_skill_name:
        raise HTTPException(status_code=400, detail="invalid_request")

    entry = _get_entry_or_404(import_id)

    if entry.record.activation_status == SkillActivationStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="skill_import_already_active")
    if entry.record.lifecycle_state != SkillImportLifecycleState.ACTIVATION_READY:
        raise HTTPException(status_code=422, detail="skill_activation_ineligible")
    if entry.record.skill_name != request.target_skill_name:
        raise HTTPException(status_code=400, detail="invalid_request")

    active_entries = [
        item
        for item in skill_import_store.list_entries()
        if item.record.skill_name == request.target_skill_name
        and item.record.activation_status == SkillActivationStatus.ACTIVE
    ]
    if len(active_entries) != 1:
        raise HTTPException(status_code=409, detail="skill_replacement_conflict")

    superseded_entry = active_entries[0]
    superseded_entry.record.lifecycle_state = SkillImportLifecycleState.SUPERSEDED
    superseded_entry.record.activation_status = SkillActivationStatus.SUPERSEDED
    superseded_entry.record.superseded_by_import_id = entry.record.id

    entry.record.lifecycle_state = SkillImportLifecycleState.ACTIVE
    entry.record.activation_status = SkillActivationStatus.ACTIVE
    entry.record.supersedes_import_id = superseded_entry.record.id

    _save_entry(superseded_entry)
    _save_entry(entry)

    return {
        "activated_import_id": entry.record.id,
        "superseded_import_id": superseded_entry.record.id,
        "skill_name": entry.record.skill_name,
        "active_version": entry.record.skill_version,
    }
