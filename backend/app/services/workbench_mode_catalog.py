from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, computed_field
import yaml


class WorkbenchModeEntryPoint(BaseModel):
    kind: str
    label: str
    description: str | None = None


class WorkbenchModeShortcut(BaseModel):
    command: str
    label: str
    description: str | None = None
    availability: str = "manual"


class WorkbenchModeOutput(BaseModel):
    kind: str
    label: str
    description: str | None = None
    workspace_attachment: str = "not_applicable"
    provenance: str = "optional"
    reusable_across_sessions: bool = False


class WorkbenchModeRouting(BaseModel):
    target: str
    activation: str
    prompt_policy: str
    tool_policy: str


class WorkbenchModeContract(BaseModel):
    id: str
    name: str
    capability: str
    purpose: str
    presentation: str
    workflow_status: str
    product_boundary: str
    suggested_phase: str
    visible_entry_points: list[WorkbenchModeEntryPoint]
    shortcuts: list[WorkbenchModeShortcut] = Field(default_factory=list)
    expected_outputs: list[WorkbenchModeOutput]
    safety_labels: list[str] = Field(default_factory=list)
    safety_boundaries: list[str]
    routing: WorkbenchModeRouting
    source_specs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def optional_shortcuts(self) -> list[str]:
        return [shortcut.command for shortcut in self.shortcuts]

    def to_public_payload(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["optional_shortcuts"] = self.optional_shortcuts
        return data


class WorkbenchModeSpec(WorkbenchModeContract):
    source_path: Path

    @property
    def payload(self) -> dict[str, Any]:
        return WorkbenchModeContract.model_validate(self).to_public_payload()


class WorkbenchModeCatalog:
    _DEFAULT_ID_ORDER = [
        "clarify-mode",
        "session-handoff",
        "discovery-questionnaire",
        "deep-research",
        "workspace-glossary",
        "agent-instruction-review",
    ]

    _REQUIRED_FIELDS = (
        "id",
        "name",
        "capability",
        "purpose",
        "presentation",
        "workflow_status",
        "product_boundary",
        "suggested_phase",
        "visible_entry_points",
        "routing",
        "expected_outputs",
        "safety_boundaries",
    )

    def __init__(self, workbench_modes_dir: str | None = None):
        backend_dir = Path(__file__).resolve().parents[2]
        self.workbench_modes_dir = (
            Path(workbench_modes_dir)
            if workbench_modes_dir is not None
            else backend_dir / "data" / "builtin" / "workbench_modes"
        )

    def list_workbench_modes(self) -> list[WorkbenchModeSpec]:
        specs: list[WorkbenchModeSpec] = []
        seen_ids: dict[str, Path] = {}
        if not self.workbench_modes_dir.exists():
            return specs

        for path in self._definition_files():
            payload = self._load_yaml(path)
            self._validate_payload(path, payload)
            mode_id = str(payload["id"])
            if mode_id in seen_ids:
                first_path = seen_ids[mode_id]
                raise ValueError(
                    f"Workbench mode yaml duplicate id '{mode_id}' in {first_path.name} and {path.name}"
                )
            seen_ids[mode_id] = path
            try:
                specs.append(WorkbenchModeSpec.model_validate({**payload, "source_path": path}))
            except ValidationError as exc:
                raise ValueError(f"Invalid workbench mode yaml: {path.name}") from exc

        order_index = {
            mode_id: idx for idx, mode_id in enumerate(self._DEFAULT_ID_ORDER)
        }
        specs.sort(key=lambda spec: (order_index.get(spec.id, len(order_index)), spec.id))
        return specs

    def get_workbench_mode(self, mode_id: str) -> WorkbenchModeSpec | None:
        for spec in self.list_workbench_modes():
            if spec.id == mode_id:
                return spec
        return None

    def _definition_files(self) -> list[Path]:
        files = list(self.workbench_modes_dir.glob("*.yaml")) + list(
            self.workbench_modes_dir.glob("*.yml")
        )
        return sorted(files, key=lambda path: path.name)

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Failed to parse workbench mode yaml: {path.name}") from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Workbench mode yaml must be a mapping object: {path.name}"
            )
        return data

    def _validate_payload(self, path: Path, payload: dict[str, Any]) -> None:
        missing = [field for field in self._REQUIRED_FIELDS if not payload.get(field)]
        if missing:
            raise ValueError(
                f"Workbench mode yaml missing required fields ({', '.join(missing)}): {path.name}"
            )

        list_fields = (
            "visible_entry_points",
            "expected_outputs",
            "safety_boundaries",
        )
        invalid_list_fields = [
            field for field in list_fields if not isinstance(payload.get(field), list)
        ]
        if invalid_list_fields:
            raise ValueError(
                f"Workbench mode yaml fields must be lists ({', '.join(invalid_list_fields)}): {path.name}"
            )
