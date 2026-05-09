from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SetupRuntime = Literal["python", "node"]


class InstallSetupSpec(BaseModel):
    runtime: SetupRuntime
    commands: List[str] = Field(default_factory=list)


class SetupValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    setup: Optional[InstallSetupSpec] = None

