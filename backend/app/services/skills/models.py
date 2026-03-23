from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SkillDirectorySpec(BaseModel):
    layer: str
    path: str


class SkillConstraints(BaseModel):
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    allowed_tools: Optional[List[str]] = None


class SkillSpec(BaseModel):
    name: str
    version: str
    description: str
    capabilities: List[str]
    entrypoint: str
    inputs_schema: Optional[Dict[str, Any]] = None
    outputs_schema: Optional[Dict[str, Any]] = None
    constraints: Optional[SkillConstraints] = None
    compatibility: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    requires: Optional[Dict[str, List[str]]] = None
    os: Optional[List[str]] = None
    install: Optional[Dict[str, Any]] = None
    homepage: Optional[str] = None
    emoji: Optional[str] = None
    always: Optional[bool] = None
    availability: Optional[bool] = True
    missing_requirements: Optional[Dict[str, List[str]]] = None

    # Sections parsed from Markdown
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    examples: Optional[str] = None
    failure_handling: Optional[str] = None

    # Metadata
    source_path: Optional[str] = None
    source_layer: Optional[str] = None
    source_dir: Optional[str] = None
    override_from: Optional[str] = None


class SkillSummary(BaseModel):
    name: str
    description: str
    availability: Optional[bool] = True
    source_path: Optional[str] = None
    source_layer: Optional[str] = None
    source_dir: Optional[str] = None
    override_from: Optional[str] = None


class RuntimeCapabilityDescriptor(BaseModel):
    prompt_blocks: Dict[str, str] = Field(default_factory=dict)
    tool_policy: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    source_type: str
    name: str
    version: str


class SkillValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
