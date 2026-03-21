import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


def _default_data_dir() -> str:
    return os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))


def _timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


class SkillGroupConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    skill_refs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SkillGroupStore:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or _default_data_dir()
        self.skill_groups_file = os.path.join(self.data_dir, "skill_groups.json")
        self.skill_groups_backup_file = f"{self.skill_groups_file}.bak"
        self._lock = threading.RLock()
        self._ensure_data_file()

    def _ensure_data_file(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        if os.path.exists(self.skill_groups_file):
            return
        self._atomic_write_json(self.skill_groups_file, [])

    def _atomic_write_json(self, path: str, data) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp.{_timestamp_tag()}"
        try:
            if os.path.exists(path):
                try:
                    shutil.copy2(path, f"{path}.bak")
                except Exception:
                    pass
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def _recover_file_if_needed(self) -> bool:
        if not os.path.exists(self.skill_groups_file):
            return False
        try:
            with open(self.skill_groups_file, "r") as f:
                json.load(f)
            return True
        except Exception:
            pass
        if os.path.exists(self.skill_groups_backup_file):
            try:
                with open(self.skill_groups_backup_file, "r") as f:
                    data = json.load(f)
                self._atomic_write_json(self.skill_groups_file, data)
                return True
            except Exception:
                pass
        corrupt = f"{self.skill_groups_file}.corrupt.{_timestamp_tag()}"
        try:
            os.replace(self.skill_groups_file, corrupt)
        except Exception:
            pass
        self._atomic_write_json(self.skill_groups_file, [])
        return True

    def list_groups(self) -> List[SkillGroupConfig]:
        with self._lock:
            self._ensure_data_file()
            self._recover_file_if_needed()
            try:
                with open(self.skill_groups_file, "r") as f:
                    data = json.load(f)
            except Exception:
                data = []
            if not isinstance(data, list):
                data = []
            return [SkillGroupConfig(**item) for item in data]

    def get_group(self, group_id: str) -> Optional[SkillGroupConfig]:
        groups = self.list_groups()
        for group in groups:
            if group.id == group_id:
                return group
        return None

    def get_skill_refs_by_group_ids(self, group_ids: List[str]) -> List[str]:
        refs: List[str] = []
        for group_id in group_ids or []:
            group = self.get_group(group_id)
            if group and group.skill_refs:
                refs.extend(group.skill_refs)
        return refs

    def create_group(self, group: SkillGroupConfig) -> SkillGroupConfig:
        with self._lock:
            groups = self.list_groups()
            groups.append(group)
            self._save_groups(groups)
            return group

    def update_group(self, group_id: str, updates: dict) -> Optional[SkillGroupConfig]:
        with self._lock:
            groups = self.list_groups()
            for i, group in enumerate(groups):
                if group.id == group_id:
                    updated = group.model_dump()
                    for k, v in updates.items():
                        updated[k] = v
                    updated["updated_at"] = datetime.now()
                    new_group = SkillGroupConfig(**updated)
                    groups[i] = new_group
                    self._save_groups(groups)
                    return new_group
            return None

    def delete_group(self, group_id: str) -> bool:
        with self._lock:
            groups = self.list_groups()
            initial_len = len(groups)
            groups = [g for g in groups if g.id != group_id]
            if len(groups) < initial_len:
                self._save_groups(groups)
                return True
            return False

    def _save_groups(self, groups: List[SkillGroupConfig]) -> None:
        self._atomic_write_json(self.skill_groups_file, [g.model_dump(mode="json") for g in groups])


skill_group_store = SkillGroupStore()
