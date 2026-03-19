from typing import List

from fastapi import APIRouter, Body, HTTPException

from app.services.skill_group_store import SkillGroupConfig, skill_group_store


router = APIRouter()


@router.get("/", response_model=List[SkillGroupConfig])
async def list_skill_groups():
    return skill_group_store.list_groups()


@router.post("/", response_model=SkillGroupConfig)
async def create_skill_group(group: SkillGroupConfig):
    return skill_group_store.create_group(group)


@router.get("/{group_id}", response_model=SkillGroupConfig)
async def get_skill_group(group_id: str):
    group = skill_group_store.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Skill group not found")
    return group


@router.put("/{group_id}", response_model=SkillGroupConfig)
async def update_skill_group(group_id: str, updates: dict = Body(...)):
    updated = skill_group_store.update_group(group_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Skill group not found")
    return updated


@router.delete("/{group_id}")
async def delete_skill_group(group_id: str):
    ok = skill_group_store.delete_group(group_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill group not found")
    return {"status": "success"}
