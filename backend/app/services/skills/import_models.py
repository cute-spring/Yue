from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SkillImportSourceType(str, Enum):
    DIRECTORY = "directory"


class SkillImportLifecycleState(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SkillImportSource(BaseModel):
    source_type: SkillImportSourceType
    source_ref: Optional[str] = None


class SkillImportRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"imp_{uuid4().hex[:12]}")
    skill_name: str
    skill_version: str
    display_name: Optional[str] = None
    source_type: SkillImportSourceType
    source_ref: Optional[str] = None
    package_format: str
    lifecycle_state: SkillImportLifecycleState
    reason_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    supersedes_import_id: Optional[str] = None
    superseded_by_import_id: Optional[str] = None


class SkillCompatibilityReport(BaseModel):
    status: str
    issues: List[str] = Field(default_factory=list)
    missing_bins: List[str] = Field(default_factory=list)
    missing_env: List[str] = Field(default_factory=list)
    unsupported_tools: List[str] = Field(default_factory=list)
    os_mismatch: List[str] = Field(default_factory=list)


class SkillImportReport(BaseModel):
    import_id: str
    parse_status: str
    standard_validation_status: str
    compatibility_status: str
    activation_eligibility: str
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    compatibility_issues: List[str] = Field(default_factory=list)


class SkillPreviewResource(BaseModel):
    id: Optional[str] = None
    path: str
    kind: str


class SkillPreviewAction(BaseModel):
    id: str
    tool: Optional[str] = None
    path: Optional[str] = None
    runtime: Optional[str] = None
    approval_policy: Optional[str] = None


class SkillPreviewOverlay(BaseModel):
    provider: str
    model: Optional[str] = None
    path: str


class SkillImportPreview(BaseModel):
    skill_name: str
    skill_version: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    entrypoint: str
    required_tools: List[str] = Field(default_factory=list)
    requires_bins: List[str] = Field(default_factory=list)
    requires_env: List[str] = Field(default_factory=list)
    resources: List[SkillPreviewResource] = Field(default_factory=list)
    actions: List[SkillPreviewAction] = Field(default_factory=list)
    overlays: List[SkillPreviewOverlay] = Field(default_factory=list)
    always: Optional[bool] = None


class SkillImportStoredEntry(BaseModel):
    record: SkillImportRecord
    report: SkillImportReport
    preview: SkillImportPreview


class SkillImportResult(BaseModel):
    record: SkillImportRecord
    report: SkillImportReport
    preview: SkillImportPreview
