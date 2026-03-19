import os

from app.services.skill_group_store import SkillGroupConfig, SkillGroupStore


def test_create_and_list_skill_groups(tmp_path):
    store = SkillGroupStore(data_dir=str(tmp_path))
    created = store.create_group(
        SkillGroupConfig(
            name="backend-debug",
            skill_refs=["backend-api-debugger:1.0.0"],
        )
    )
    groups = store.list_groups()
    assert created.name == "backend-debug"
    assert any(g.id == created.id for g in groups)


def test_update_and_delete_skill_group(tmp_path):
    store = SkillGroupStore(data_dir=str(tmp_path))
    created = store.create_group(
        SkillGroupConfig(
            name="frontend-core",
            skill_refs=["frontend-patterns:1.0.0"],
        )
    )

    updated = store.update_group(
        created.id,
        {"description": "frontend defaults", "skill_refs": ["frontend-patterns:2.0.0"]},
    )
    assert updated is not None
    assert updated.description == "frontend defaults"
    assert updated.skill_refs == ["frontend-patterns:2.0.0"]

    assert store.delete_group(created.id) is True
    assert store.get_group(created.id) is None


def test_skill_group_store_persists_json_file(tmp_path):
    store = SkillGroupStore(data_dir=str(tmp_path))
    store.create_group(
        SkillGroupConfig(
            name="ops",
            skill_refs=["incident-debugger:1.0.0"],
        )
    )
    assert os.path.exists(os.path.join(tmp_path, "skill_groups.json"))
