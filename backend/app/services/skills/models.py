from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SkillDirectorySpec(BaseModel):
    layer: str
    path: str


class SkillConstraints(BaseModel):
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    allowed_tools: Optional[List[str]] = None


class SkillLoadingPolicy(BaseModel):
    summary_fields: List[str] = Field(default_factory=list)
    default_tier: str = "prompt"


class SkillResourceSpec(BaseModel):
    id: Optional[str] = None
    path: str
    kind: str
    load_tier: str = "reference"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SkillReferenceSpec(SkillResourceSpec):
    resource_type: Literal["reference"] = "reference"


class SkillScriptSpec(SkillResourceSpec):
    resource_type: Literal["script"] = "script"
    runtime: Optional[str] = None
    safety: Optional[str] = None


class SkillOverlaySpec(BaseModel):
    provider: str
    path: str
    model: Optional[str] = None
    models: List[str] = Field(default_factory=list)
    kind: str = "yaml"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SkillActionSpec(BaseModel):
    id: str
    tool: Optional[str] = None
    resource: Optional[str] = None
    path: Optional[str] = None
    runtime: Optional[str] = None
    load_tier: str = "action"
    safety: Optional[str] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    approval_policy: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeSkillActionDescriptor(BaseModel):
    id: str
    name: str
    version: str
    tool: Optional[str] = None
    resource: Optional[str] = None
    path: Optional[str] = None
    runtime: Optional[str] = None
    load_tier: str = "action"
    safety: Optional[str] = None
    approval_policy: Optional[str] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeSkillActionInvocationRequest(BaseModel):
    skill_name: str
    skill_version: str
    action_id: str
    provider: Optional[str] = None
    model_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    enabled_tools: List[str] = Field(default_factory=list)


class RuntimeSkillActionInvocationResult(BaseModel):
    accepted: bool
    skill_name: str
    skill_version: str
    action_id: str
    descriptor: Optional[RuntimeSkillActionDescriptor] = None
    approval_required: bool = False
    approval_policy: Optional[str] = None
    mapped_tool: Optional[str] = None
    missing_requirements: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    execution_mode: str = "tool_only"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeSkillActionExecutionRequest(BaseModel):
    invocation: RuntimeSkillActionInvocationRequest
    request_id: Optional[str] = None


class RuntimeSkillActionApprovalRequest(BaseModel):
    skill_name: str
    skill_version: str
    action_id: str
    approved: bool
    approval_token: Optional[str] = None
    request_id: Optional[str] = None


class RuntimeSkillActionApprovalResult(BaseModel):
    approved: bool
    status: str
    lifecycle_phase: str = "approval"
    lifecycle_status: str
    approval_token: Optional[str] = None
    invocation: RuntimeSkillActionInvocationResult
    request_id: Optional[str] = None
    event_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeSkillActionExecutionResult(BaseModel):
    status: str
    lifecycle_phase: str = "preflight"
    lifecycle_status: str = "preflight_ready"
    invocation: RuntimeSkillActionInvocationResult
    execution_mode: str = "non_executing"
    request_id: Optional[str] = None
    event_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SkillPackageSpec(BaseModel):
    format_version: int = 1
    package_format: str = "package_directory"
    name: str
    version: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    entrypoint: str
    constraints: Optional[SkillConstraints] = None
    compatibility: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    requires: Optional[Dict[str, List[str]]] = None
    os: Optional[List[str]] = None
    install: Optional[Dict[str, Any]] = None
    homepage: Optional[str] = None
    emoji: Optional[str] = None
    always: Optional[bool] = None
    loading: SkillLoadingPolicy = Field(default_factory=SkillLoadingPolicy)
    resources: List[SkillResourceSpec] = Field(default_factory=list)
    references: List[SkillReferenceSpec] = Field(default_factory=list)
    scripts: List[SkillScriptSpec] = Field(default_factory=list)
    overlays: List[SkillOverlaySpec] = Field(default_factory=list)
    actions: List[SkillActionSpec] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    examples: Optional[str] = None
    failure_handling: Optional[str] = None
    source_path: Optional[str] = None
    source_layer: Optional[str] = None
    source_dir: Optional[str] = None
    manifest_path: Optional[str] = None
    skill_markdown_path: Optional[str] = None
    override_from: Optional[str] = None


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
    package_format: Optional[str] = None
    manifest_path: Optional[str] = None


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
    actions: List[RuntimeSkillActionDescriptor] = Field(default_factory=list)
    source_type: str
    name: str
    version: str


class SkillValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
