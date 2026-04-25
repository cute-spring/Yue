from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BuiltinAgentSpec:
    id: str
    payload: dict[str, Any]
    source_path: Path


class BuiltinAgentCatalog:
    _DEFAULT_ID_ORDER = [
        "builtin-docs",
        "builtin-local-docs",
        "builtin-architect",
        "builtin-excel-analyst",
        "builtin-pdf-research",
        "builtin-ppt-builder",
        "builtin-action-lab",
        "builtin-translator",
    ]

    def __init__(self, builtin_agents_dir: str | None = None):
        backend_dir = Path(__file__).resolve().parents[2]
        self.builtin_agents_dir = (
            Path(builtin_agents_dir)
            if builtin_agents_dir is not None
            else backend_dir / "data" / "builtin" / "agents"
        )

    def list_builtin_agents(self) -> list[BuiltinAgentSpec]:
        specs: list[BuiltinAgentSpec] = []
        seen_ids: dict[str, Path] = {}
        if not self.builtin_agents_dir.exists():
            return specs

        for path in self._definition_files():
            payload = self._load_yaml(path)
            self._validate_payload(path, payload)
            builtin_id = str(payload["id"])
            if builtin_id in seen_ids:
                first_path = seen_ids[builtin_id]
                raise ValueError(
                    f"Builtin agent yaml duplicate id '{builtin_id}' in {first_path.name} and {path.name}"
                )
            seen_ids[builtin_id] = path
            specs.append(
                BuiltinAgentSpec(
                    id=builtin_id,
                    payload=payload,
                    source_path=path,
                )
            )
        order_index = {
            agent_id: idx for idx, agent_id in enumerate(self._DEFAULT_ID_ORDER)
        }
        specs.sort(key=lambda spec: (order_index.get(spec.id, len(order_index)), spec.id))
        return specs

    def _definition_files(self) -> list[Path]:
        files = list(self.builtin_agents_dir.glob("*.yaml")) + list(
            self.builtin_agents_dir.glob("*.yml")
        )
        return sorted(files, key=lambda p: p.name)

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Failed to parse builtin agent yaml: {path.name}") from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Builtin agent yaml must be a mapping object: {path.name}"
            )
        return data

    def _validate_payload(self, path: Path, payload: dict[str, Any]) -> None:
        required_fields = ("id", "name", "system_prompt")
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            raise ValueError(
                f"Builtin agent yaml missing required fields ({', '.join(missing)}): {path.name}"
            )
