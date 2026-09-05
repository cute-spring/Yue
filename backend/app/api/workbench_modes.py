from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.workbench_mode_catalog import (
    WorkbenchModeCatalog,
    WorkbenchModeContract,
    WorkbenchModeSpec,
)


router = APIRouter()


def _catalog() -> WorkbenchModeCatalog:
    return WorkbenchModeCatalog()


def _to_public_mode(spec: WorkbenchModeSpec) -> dict:
    return spec.payload


@router.get("/", response_model=list[WorkbenchModeContract])
async def list_workbench_modes():
    return [_to_public_mode(spec) for spec in _catalog().list_workbench_modes()]


@router.get("/{mode_id}", response_model=WorkbenchModeContract)
async def get_workbench_mode(mode_id: str):
    spec = _catalog().get_workbench_mode(mode_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="workbench_mode_not_found")
    return _to_public_mode(spec)
