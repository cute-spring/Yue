from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime
from typing import List, Optional

from pydantic import ValidationError

from app.services.skills.import_models import (
    SkillImportRecord,
    SkillImportStoredEntry,
    SkillPreflightRecord,
)


def _default_data_dir() -> str:
    return os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))


def _timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


class SkillImportStore:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or _default_data_dir()
        self.imports_file = os.path.join(self.data_dir, "skill_imports.json")
        self.imports_backup_file = f"{self.imports_file}.bak"
        self.preflight_file = os.path.join(self.data_dir, "skill_preflight.json")
        self.preflight_backup_file = f"{self.preflight_file}.bak"
        self._lock = threading.RLock()
        self._ensure_data_file()

    def _ensure_data_file(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        if os.path.exists(self.imports_file):
            if os.path.exists(self.preflight_file):
                return
        if not os.path.exists(self.imports_file):
            self._atomic_write_json(self.imports_file, [])
        if not os.path.exists(self.preflight_file):
            self._atomic_write_json(self.preflight_file, [])

    def _atomic_write_json(self, path: str, data) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp.{_timestamp_tag()}"
        try:
            if os.path.exists(path):
                try:
                    shutil.copy2(path, f"{path}.bak")
                except Exception:
                    pass
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def _recover_file_if_needed(self) -> bool:
        if not os.path.exists(self.imports_file):
            return False
        try:
            with open(self.imports_file, "r", encoding="utf-8") as handle:
                json.load(handle)
            return True
        except Exception:
            pass
        if os.path.exists(self.imports_backup_file):
            try:
                with open(self.imports_backup_file, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._atomic_write_json(self.imports_file, data)
                return True
            except Exception:
                pass
        corrupt = f"{self.imports_file}.corrupt.{_timestamp_tag()}"
        try:
            os.replace(self.imports_file, corrupt)
        except Exception:
            pass
        self._atomic_write_json(self.imports_file, [])
        return True

    def _load_entries(self) -> List[SkillImportStoredEntry]:
        self._ensure_data_file()
        self._recover_file_if_needed()
        try:
            with open(self.imports_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            data = []
        if not isinstance(data, list):
            data = []
        entries: List[SkillImportStoredEntry] = []
        for item in data:
            try:
                entries.append(SkillImportStoredEntry(**item))
            except ValidationError:
                continue
        return entries

    def _save_entries(self, entries: List[SkillImportStoredEntry]) -> None:
        self._atomic_write_json(self.imports_file, [item.model_dump(mode="json") for item in entries])

    def list_entries(self) -> List[SkillImportStoredEntry]:
        with self._lock:
            return self._load_entries()

    def list_records(self) -> List[SkillImportRecord]:
        return [entry.record for entry in self.list_entries()]

    def get_entry(self, import_id: str) -> Optional[SkillImportStoredEntry]:
        for entry in self.list_entries():
            if entry.record.id == import_id:
                return entry
        return None

    def get_record(self, import_id: str) -> Optional[SkillImportRecord]:
        entry = self.get_entry(import_id)
        return entry.record if entry else None

    def save_entry(self, entry: SkillImportStoredEntry) -> SkillImportStoredEntry:
        with self._lock:
            entries = self._load_entries()
            updated = False
            for index, existing in enumerate(entries):
                if existing.record.id == entry.record.id:
                    entries[index] = entry
                    updated = True
                    break
            if not updated:
                entries.append(entry)
            self._save_entries(entries)
            return entry

    def _recover_preflight_file_if_needed(self) -> bool:
        if not os.path.exists(self.preflight_file):
            return False
        try:
            with open(self.preflight_file, "r", encoding="utf-8") as handle:
                json.load(handle)
            return True
        except Exception:
            pass
        if os.path.exists(self.preflight_backup_file):
            try:
                with open(self.preflight_backup_file, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._atomic_write_json(self.preflight_file, data)
                return True
            except Exception:
                pass
        corrupt = f"{self.preflight_file}.corrupt.{_timestamp_tag()}"
        try:
            os.replace(self.preflight_file, corrupt)
        except Exception:
            pass
        self._atomic_write_json(self.preflight_file, [])
        return True

    def _load_preflight_records(self) -> List[SkillPreflightRecord]:
        self._ensure_data_file()
        self._recover_preflight_file_if_needed()
        try:
            with open(self.preflight_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            data = []
        if not isinstance(data, list):
            data = []
        records: List[SkillPreflightRecord] = []
        for item in data:
            try:
                records.append(SkillPreflightRecord(**item))
            except ValidationError:
                continue
        return records

    def _save_preflight_records(self, records: List[SkillPreflightRecord]) -> None:
        self._atomic_write_json(self.preflight_file, [item.model_dump(mode="json") for item in records])

    def list_preflight_records(self) -> List[SkillPreflightRecord]:
        with self._lock:
            return self._load_preflight_records()

    def get_preflight_record(self, skill_ref: str) -> Optional[SkillPreflightRecord]:
        for item in self.list_preflight_records():
            if item.skill_ref == skill_ref:
                return item
        return None

    def save_preflight_record(self, record: SkillPreflightRecord) -> SkillPreflightRecord:
        with self._lock:
            records = self._load_preflight_records()
            updated = False
            for index, existing in enumerate(records):
                if existing.skill_ref == record.skill_ref:
                    records[index] = record
                    updated = True
                    break
            if not updated:
                records.append(record)
            self._save_preflight_records(records)
            return record

    def replace_preflight_records(self, records: List[SkillPreflightRecord]) -> List[SkillPreflightRecord]:
        with self._lock:
            self._save_preflight_records(records)
            return records
