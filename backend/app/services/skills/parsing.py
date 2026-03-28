import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.services.skills.models import (
    SkillActionSpec,
    SkillConstraints,
    SkillLoadingPolicy,
    SkillOverlaySpec,
    SkillPackageSpec,
    SkillReferenceSpec,
    SkillResourceSpec,
    SkillScriptSpec,
    SkillSpec,
    SkillValidationResult,
)


logger = logging.getLogger(__name__)


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v is not None and str(v).strip()]
    if isinstance(value, str):
        val = value.strip()
        return [val] if val else []
    return []


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.exception("Error parsing yaml in %s: %s", path, exc)
        return {}


def _safe_overlay_dict(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:
        logger.exception("Error parsing overlay yaml in %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else {}


def _resource_kind_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
        return "image"
    if suffix in {".txt", ".rst"}:
        return "text"
    if suffix in {".jinja", ".j2"}:
        return "template"
    if suffix in {".py", ".sh", ".js", ".ts"}:
        return "script"
    return "file"


def _runtime_for_script(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix == ".sh":
        return "shell"
    if suffix == ".js":
        return "node"
    if suffix == ".ts":
        return "typescript"
    return None


def _path_exists(package_dir: Path, rel_path: Optional[str]) -> bool:
    if not rel_path:
        return False
    return (package_dir / rel_path).exists()


def _normalize_resource_id(path: str, explicit_id: Optional[str] = None) -> str:
    if explicit_id and explicit_id.strip():
        return explicit_id.strip()
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", path.strip()).strip("-")
    return normalized or "resource"


def _normalize_overlay_model_values(value: Any) -> List[str]:
    return [item.strip() for item in _normalize_list(value) if item.strip()]


class SkillLoader:
    """
    Discovery, parse, and normalize skills from markdown files and package directories.
    """

    @staticmethod
    def detect_format(path: str | Path) -> str:
        candidate = Path(path)
        if candidate.is_dir() and (candidate / "SKILL.md").exists():
            return "package_directory"
        if candidate.is_file() and candidate.suffix.lower() == ".md":
            return "legacy_markdown"
        return "unknown"

    @staticmethod
    def _parse_markdown_sections(content: str) -> tuple[Optional[Dict[str, Any]], Dict[str, str]]:
        parts = re.split(r"^---\s*$", content, flags=re.MULTILINE)
        if len(parts) < 3:
            return None, {}

        frontmatter_raw = parts[1].strip()
        markdown_content = "---".join(parts[2:]).strip()
        frontmatter = yaml.safe_load(frontmatter_raw)
        if not isinstance(frontmatter, dict):
            return None, {}

        sections: Dict[str, str] = {}
        current_section = None
        section_content: List[str] = []

        for line in markdown_content.splitlines():
            match = re.match(r"^##\s+(.+)$", line)
            if match:
                if current_section:
                    sections[current_section] = "\n".join(section_content).strip()
                current_section = match.group(1).strip().lower().replace(" ", "_")
                section_content = []
            elif current_section:
                section_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(section_content).strip()

        return frontmatter, sections

    @staticmethod
    def parse_markdown(content: str, source_path: str = None) -> Optional[SkillSpec]:
        try:
            frontmatter, sections = SkillLoader._parse_markdown_sections(content)
            if frontmatter is None:
                logger.error("Invalid skill format in %s", source_path)
                return None

            raw_requires = frontmatter.get("requires")
            requires = None
            if isinstance(raw_requires, dict):
                bins = _normalize_list(raw_requires.get("bins") or raw_requires.get("bin"))
                env = _normalize_list(raw_requires.get("env"))
                requires = {"bins": bins, "env": env}
            elif isinstance(raw_requires, list) or isinstance(raw_requires, str):
                requires = {"bins": _normalize_list(raw_requires), "env": []}

            raw_os = frontmatter.get("os")
            os_list = _normalize_list(raw_os)
            os_list = [o.lower() for o in os_list] if os_list else None

            metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else None
            install = frontmatter.get("install") if isinstance(frontmatter.get("install"), dict) else None

            skill_data = {**frontmatter}
            skill_data["system_prompt"] = sections.get("system_prompt")
            skill_data["instructions"] = sections.get("instructions")
            skill_data["examples"] = sections.get("examples")
            skill_data["failure_handling"] = sections.get("failure_handling")
            skill_data["source_path"] = source_path
            skill_data["requires"] = requires
            skill_data["os"] = os_list
            skill_data["metadata"] = metadata
            skill_data["install"] = install

            return SkillSpec(**skill_data)
        except Exception as exc:
            logger.exception("Error parsing skill in %s: %s", source_path, exc)
            return None

    @staticmethod
    def _discover_reference_specs(package_dir: Path) -> List[SkillReferenceSpec]:
        references_dir = package_dir / "references"
        if not references_dir.exists():
            return []

        references: List[SkillReferenceSpec] = []
        for path in sorted(p for p in references_dir.rglob("*") if p.is_file()):
            rel_path = str(path.relative_to(package_dir))
            references.append(
                SkillReferenceSpec(
                    id=path.stem,
                    path=rel_path,
                    kind=_resource_kind_for_path(path),
                    load_tier="reference",
                )
            )
        return references

    @staticmethod
    def _discover_script_specs(package_dir: Path) -> List[SkillScriptSpec]:
        scripts_dir = package_dir / "scripts"
        if not scripts_dir.exists():
            return []

        scripts: List[SkillScriptSpec] = []
        for path in sorted(p for p in scripts_dir.rglob("*") if p.is_file()):
            rel_path = str(path.relative_to(package_dir))
            scripts.append(
                SkillScriptSpec(
                    id=path.stem,
                    path=rel_path,
                    kind=_resource_kind_for_path(path),
                    load_tier="action",
                    runtime=_runtime_for_script(path),
                )
            )
        return scripts

    @staticmethod
    def _discover_overlay_specs(package_dir: Path) -> List[SkillOverlaySpec]:
        agents_dir = package_dir / "agents"
        if not agents_dir.exists():
            return []

        overlays: List[SkillOverlaySpec] = []
        for path in sorted(p for p in agents_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}):
            rel_path = str(path.relative_to(package_dir))
            filename_parts = path.stem.split(".", 1)
            provider = filename_parts[0]
            model = filename_parts[1] if len(filename_parts) > 1 else None
            overlays.append(
                SkillOverlaySpec(
                    provider=provider,
                    path=rel_path,
                    model=model,
                    kind="yaml",
                )
            )
        return overlays

    @staticmethod
    def _resources_from_components(
        references: List[SkillReferenceSpec],
        scripts: List[SkillScriptSpec],
    ) -> List[SkillResourceSpec]:
        resources: List[SkillResourceSpec] = []
        for item in references:
            resources.append(
                SkillResourceSpec(
                    id=item.id,
                    path=item.path,
                    kind=item.kind,
                    load_tier=item.load_tier,
                    metadata={"resource_type": "reference"},
                )
            )
        for item in scripts:
            metadata = {"resource_type": "script"}
            if item.runtime:
                metadata["runtime"] = item.runtime
            if item.safety:
                metadata["safety"] = item.safety
            resources.append(
                SkillResourceSpec(
                    id=item.id,
                    path=item.path,
                    kind=item.kind,
                    load_tier=item.load_tier,
                    metadata=metadata,
                )
            )
        return resources

    @staticmethod
    def _normalize_reference_spec(item: Dict[str, Any], package_dir: Path) -> SkillReferenceSpec:
        path = str(item.get("path") or "").strip()
        file_path = package_dir / path if path else package_dir
        return SkillReferenceSpec(
            id=_normalize_resource_id(path, item.get("id")),
            path=path,
            kind=str(item.get("kind") or _resource_kind_for_path(file_path)),
            load_tier=str(item.get("load_tier") or "reference"),
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )

    @staticmethod
    def _normalize_script_spec(item: Dict[str, Any], package_dir: Path) -> SkillScriptSpec:
        path = str(item.get("path") or "").strip()
        file_path = package_dir / path if path else package_dir
        return SkillScriptSpec(
            id=_normalize_resource_id(path, item.get("id")),
            path=path,
            kind=str(item.get("kind") or _resource_kind_for_path(file_path)),
            load_tier=str(item.get("load_tier") or "action"),
            runtime=_runtime_for_script(file_path) if not item.get("runtime") else str(item.get("runtime")),
            safety=item.get("safety"),
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )

    @staticmethod
    def _normalize_overlay_spec(item: Dict[str, Any]) -> Optional[SkillOverlaySpec]:
        path = str(item.get("path") or "").strip()
        provider = str(item.get("provider") or "").strip()
        if not path or not provider:
            return None
        model = str(item.get("model") or "").strip() or None
        models = _normalize_overlay_model_values(item.get("models"))
        if model and model not in models:
            models = [model, *models]
        return SkillOverlaySpec(
            provider=provider,
            path=path,
            model=model,
            models=models,
            kind=str(item.get("kind") or "yaml"),
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )

    @staticmethod
    def _normalize_action_spec(item: Dict[str, Any]) -> Optional[SkillActionSpec]:
        action_id = str(item.get("id") or "").strip()
        if not action_id:
            return None
        return SkillActionSpec(
            id=action_id,
            tool=str(item.get("tool") or "").strip() or None,
            resource=item.get("resource"),
            path=item.get("path"),
            runtime=item.get("runtime"),
            load_tier=str(item.get("load_tier") or "action"),
            safety=item.get("safety"),
            input_schema=item.get("input_schema") if isinstance(item.get("input_schema"), dict) else {},
            output_schema=item.get("output_schema") if isinstance(item.get("output_schema"), dict) else {},
            approval_policy=item.get("approval_policy"),
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )

    @staticmethod
    def _normalize_resources(
        references: List[SkillReferenceSpec],
        scripts: List[SkillScriptSpec],
    ) -> tuple[List[SkillReferenceSpec], List[SkillScriptSpec], List[SkillResourceSpec]]:
        normalized_references = [
            ref.model_copy(update={"id": _normalize_resource_id(ref.path, ref.id), "load_tier": ref.load_tier or "reference"})
            for ref in references
        ]
        normalized_scripts = [
            script.model_copy(
                update={
                    "id": _normalize_resource_id(script.path, script.id),
                    "load_tier": script.load_tier or "action",
                }
            )
            for script in scripts
        ]
        return normalized_references, normalized_scripts, SkillLoader._resources_from_components(normalized_references, normalized_scripts)

    @staticmethod
    def _normalize_actions(actions: List[SkillActionSpec], scripts: List[SkillScriptSpec]) -> List[SkillActionSpec]:
        script_by_id = {script.id: script for script in scripts if script.id}
        script_by_path = {script.path: script for script in scripts if script.path}
        normalized_actions: List[SkillActionSpec] = []
        for action in actions:
            normalized = action.model_copy(deep=True)
            if normalized.resource and normalized.resource in script_by_path and normalized.resource not in script_by_id:
                normalized.resource = script_by_path[normalized.resource].id
            if not normalized.path and normalized.resource in script_by_id:
                target_script = script_by_id[normalized.resource]
                normalized.path = target_script.path
                if not normalized.runtime:
                    normalized.runtime = target_script.runtime
                if not normalized.safety:
                    normalized.safety = target_script.safety
            normalized_actions.append(normalized)
        return normalized_actions

    @staticmethod
    def derive_minimal_manifest(skill: SkillSpec, package_dir: str | Path) -> SkillPackageSpec:
        package_root = Path(package_dir)
        references = SkillLoader._discover_reference_specs(package_root)
        scripts = SkillLoader._discover_script_specs(package_root)
        overlays = SkillLoader._discover_overlay_specs(package_root)
        references, scripts, resources = SkillLoader._normalize_resources(references, scripts)

        metadata = dict(skill.metadata or {})
        metadata.setdefault("generated_manifest", True)

        return SkillPackageSpec(
            format_version=1,
            package_format="package_directory",
            name=skill.name,
            version=skill.version,
            description=skill.description,
            capabilities=list(skill.capabilities or []),
            entrypoint=skill.entrypoint,
            constraints=skill.constraints,
            compatibility=skill.compatibility,
            metadata=metadata,
            requires=skill.requires,
            os=skill.os,
            install=skill.install,
            homepage=skill.homepage,
            emoji=skill.emoji,
            always=skill.always,
            loading=SkillLoadingPolicy(summary_fields=["name", "description", "capabilities"], default_tier="prompt"),
            resources=resources,
            references=references,
            scripts=scripts,
            overlays=overlays,
            actions=[],
            system_prompt=skill.system_prompt,
            instructions=skill.instructions,
            examples=skill.examples,
            failure_handling=skill.failure_handling,
            source_path=skill.source_path,
            source_dir=str(package_root),
            skill_markdown_path=skill.source_path,
        )

    @staticmethod
    def parse_package(package_dir: str | Path) -> Optional[SkillPackageSpec]:
        package_root = Path(package_dir)
        skill_path = package_root / "SKILL.md"
        if not skill_path.exists():
            logger.error("Package skill missing SKILL.md: %s", package_root)
            return None

        skill = SkillLoader.parse_markdown(skill_path.read_text(), source_path=str(skill_path))
        if not skill:
            return None

        manifest_path = package_root / "manifest.yaml"
        if not manifest_path.exists():
            package = SkillLoader.derive_minimal_manifest(skill, package_root)
            package.skill_markdown_path = str(skill_path)
            package.manifest_path = None
            return package

        manifest = _load_yaml_file(manifest_path)
        loading_data = manifest.get("loading") if isinstance(manifest.get("loading"), dict) else {}
        resources_data = manifest.get("resources") if isinstance(manifest.get("resources"), dict) else {}
        has_declared_references = "references" in resources_data
        has_declared_scripts = "scripts" in resources_data
        references_data = resources_data.get("references") if isinstance(resources_data.get("references"), list) else []
        scripts_data = resources_data.get("scripts") if isinstance(resources_data.get("scripts"), list) else []
        overlays_data = manifest.get("overlays") if isinstance(manifest.get("overlays"), dict) else {}
        has_declared_overlays = "providers" in overlays_data
        providers_data = overlays_data.get("providers") if isinstance(overlays_data.get("providers"), list) else []
        actions_data = manifest.get("actions") if isinstance(manifest.get("actions"), list) else []

        references = [
            SkillLoader._normalize_reference_spec(item, package_root)
            for item in references_data
            if isinstance(item, dict)
        ]
        scripts = [
            SkillLoader._normalize_script_spec(item, package_root)
            for item in scripts_data
            if isinstance(item, dict)
        ]
        overlays = [
            overlay
            for overlay in (SkillLoader._normalize_overlay_spec(item) for item in providers_data if isinstance(item, dict))
            if overlay is not None
        ]
        actions = [
            action
            for action in (SkillLoader._normalize_action_spec(item) for item in actions_data if isinstance(item, dict))
            if action is not None
        ]

        if not has_declared_references:
            references = SkillLoader._discover_reference_specs(package_root)
        if not has_declared_scripts:
            scripts = SkillLoader._discover_script_specs(package_root)
        if not has_declared_overlays:
            overlays = SkillLoader._discover_overlay_specs(package_root)

        references, scripts, resources = SkillLoader._normalize_resources(references, scripts)
        actions = SkillLoader._normalize_actions(actions, scripts)

        metadata = dict(skill.metadata or {})
        manifest_metadata = manifest.get("metadata") if isinstance(manifest.get("metadata"), dict) else {}
        metadata.update(manifest_metadata)

        loading = SkillLoadingPolicy(
            summary_fields=_normalize_list(loading_data.get("summary_fields")) or ["name", "description", "capabilities"],
            default_tier=str(loading_data.get("default_tier") or "prompt"),
        )

        return SkillPackageSpec(
            format_version=int(manifest.get("format_version") or 1),
            package_format="package_directory",
            name=str(manifest.get("name") or skill.name),
            version=str(manifest.get("version") or skill.version),
            description=str(manifest.get("description") or skill.description),
            capabilities=_normalize_list(manifest.get("capabilities")) or list(skill.capabilities or []),
            entrypoint=str(manifest.get("entrypoint") or skill.entrypoint),
            constraints=skill.constraints,
            compatibility=manifest.get("compatibility") if isinstance(manifest.get("compatibility"), dict) else skill.compatibility,
            metadata=metadata,
            requires=skill.requires,
            os=skill.os,
            install=skill.install,
            homepage=str(manifest.get("homepage") or skill.homepage or "") or None,
            emoji=str(manifest.get("emoji") or skill.emoji or "") or None,
            always=bool(manifest.get("always")) if manifest.get("always") is not None else skill.always,
            loading=loading,
            resources=resources,
            references=references,
            scripts=scripts,
            overlays=overlays,
            actions=actions,
            system_prompt=skill.system_prompt,
            instructions=skill.instructions,
            examples=skill.examples,
            failure_handling=skill.failure_handling,
            source_path=str(skill_path),
            source_dir=str(package_root),
            manifest_path=str(manifest_path),
            skill_markdown_path=str(skill_path),
        )

    @staticmethod
    def build_package_from_legacy_markdown(source_path: str | Path) -> Optional[SkillPackageSpec]:
        markdown_path = Path(source_path)
        skill = SkillLoader.parse_markdown(markdown_path.read_text(), source_path=str(markdown_path))
        if not skill:
            return None

        metadata = dict(skill.metadata or {})
        metadata.setdefault("generated_manifest", True)

        return SkillPackageSpec(
            format_version=1,
            package_format="legacy_markdown",
            name=skill.name,
            version=skill.version,
            description=skill.description,
            capabilities=list(skill.capabilities or []),
            entrypoint=skill.entrypoint,
            constraints=skill.constraints,
            compatibility=skill.compatibility,
            metadata=metadata,
            requires=skill.requires,
            os=skill.os,
            install=skill.install,
            homepage=skill.homepage,
            emoji=skill.emoji,
            always=skill.always,
            loading=SkillLoadingPolicy(summary_fields=["name", "description", "capabilities"], default_tier="prompt"),
            resources=[],
            references=[],
            scripts=[],
            overlays=[],
            actions=[],
            system_prompt=skill.system_prompt,
            instructions=skill.instructions,
            examples=skill.examples,
            failure_handling=skill.failure_handling,
            source_path=str(markdown_path),
            source_dir=str(markdown_path.parent),
            skill_markdown_path=str(markdown_path),
        )

    @staticmethod
    def package_to_skill_spec(package: SkillPackageSpec) -> SkillSpec:
        metadata = dict(package.metadata or {})
        package_actions = [
            {
                "id": action.id,
                "tool": action.tool,
                "resource": action.resource,
                "path": action.path,
                "runtime": action.runtime,
                "load_tier": action.load_tier,
                "safety": action.safety,
                "approval_policy": action.approval_policy,
                "input_schema": action.input_schema,
                "output_schema": action.output_schema,
                "metadata": action.metadata,
            }
            for action in package.actions
        ]
        metadata.setdefault(
            "package",
            {
                "format_version": package.format_version,
                "package_format": package.package_format,
                "resource_count": len(package.resources),
                "reference_count": len(package.references),
                "script_count": len(package.scripts),
                "overlay_count": len(package.overlays),
                "action_count": len(package.actions),
            },
        )
        metadata.setdefault("package_actions", package_actions)

        return SkillSpec(
            name=package.name,
            version=package.version,
            description=package.description,
            capabilities=list(package.capabilities or []),
            entrypoint=package.entrypoint,
            constraints=package.constraints,
            compatibility=package.compatibility,
            metadata=metadata,
            requires=package.requires,
            os=package.os,
            install=package.install,
            homepage=package.homepage,
            emoji=package.emoji,
            always=package.always,
            system_prompt=package.system_prompt,
            instructions=package.instructions,
            examples=package.examples,
            failure_handling=package.failure_handling,
            source_path=package.source_path,
            source_layer=package.source_layer,
            source_dir=package.source_dir,
            override_from=package.override_from,
            package_format=package.package_format,
            manifest_path=package.manifest_path,
        )

    @staticmethod
    def resolve_package_overlay(
        package: SkillPackageSpec,
        *,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> SkillPackageSpec:
        if not provider:
            return package

        target_provider = provider.strip().lower()
        target_model = (model_name or "").strip().lower()

        matching_overlays = []
        for overlay in package.overlays:
            if overlay.provider.strip().lower() != target_provider:
                continue
            declared_models = [model.lower() for model in overlay.models if model]
            overlay_model = (overlay.model or "").strip().lower()
            if target_model:
                if overlay_model and overlay_model == target_model:
                    matching_overlays.append((2, overlay))
                    continue
                if declared_models and target_model in declared_models:
                    matching_overlays.append((1, overlay))
                    continue
                if overlay_model or declared_models:
                    continue
            matching_overlays.append((0, overlay))

        if not matching_overlays:
            return package

        resolved = package.model_copy(deep=True)
        package_dir = Path(package.skill_markdown_path).parent if package.skill_markdown_path else Path(package.source_dir or "")
        applied_overlays = []
        for _specificity, matching_overlay in sorted(matching_overlays, key=lambda item: item[0]):
            overlay_path = package_dir / matching_overlay.path
            overlay_payload = _safe_overlay_dict(overlay_path)
            if overlay_payload is None:
                continue

            resolved.metadata = dict(resolved.metadata or {})
            applied_overlay = {
                "provider": matching_overlay.provider,
                "path": matching_overlay.path,
            }
            if matching_overlay.model:
                applied_overlay["model"] = matching_overlay.model
            if matching_overlay.models:
                applied_overlay["models"] = list(matching_overlay.models)
            if model_name:
                applied_overlay["model_name"] = model_name
            applied_overlays.append(applied_overlay)

            for field_name in [
                "description",
                "entrypoint",
                "system_prompt",
                "instructions",
                "examples",
                "failure_handling",
                "homepage",
                "emoji",
                "always",
            ]:
                if field_name in overlay_payload and overlay_payload.get(field_name) not in (None, ""):
                    setattr(resolved, field_name, overlay_payload.get(field_name))

            if isinstance(overlay_payload.get("capabilities"), list):
                resolved.capabilities = _normalize_list(overlay_payload.get("capabilities"))
            if isinstance(overlay_payload.get("metadata"), dict):
                resolved.metadata.update(overlay_payload.get("metadata"))
            if isinstance(overlay_payload.get("compatibility"), dict):
                resolved.compatibility = dict(resolved.compatibility or {})
                resolved.compatibility.update(overlay_payload.get("compatibility"))
            if isinstance(overlay_payload.get("requires"), dict):
                merged_requires = dict(resolved.requires or {})
                overlay_requires = overlay_payload.get("requires", {})
                merged_requires["bins"] = _normalize_list(overlay_requires.get("bins")) or merged_requires.get("bins") or []
                merged_requires["env"] = _normalize_list(overlay_requires.get("env")) or merged_requires.get("env") or []
                resolved.requires = merged_requires
            if isinstance(overlay_payload.get("os"), list):
                resolved.os = [item.lower() for item in _normalize_list(overlay_payload.get("os"))]
            if isinstance(overlay_payload.get("constraints"), dict):
                constraint_data = resolved.constraints.model_dump() if resolved.constraints else {}
                constraint_data.update(overlay_payload.get("constraints"))
                resolved.constraints = SkillConstraints(**constraint_data)

            interface = overlay_payload.get("interface")
            if isinstance(interface, dict):
                resolved.metadata["interface"] = interface

            resolved.metadata["overlay_payload"] = overlay_payload

        if applied_overlays:
            resolved.metadata["resolved_overlay"] = applied_overlays[-1]
            resolved.metadata["resolved_overlays"] = applied_overlays

        return resolved

    @staticmethod
    def validate_package(package: SkillPackageSpec) -> SkillValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        package_dir = Path(package.skill_markdown_path).parent if package.skill_markdown_path else Path()
        if not package_dir.exists() and package.source_path:
            package_dir = Path(package.source_path).parent
        if not package_dir.exists() and package.source_dir:
            package_dir = Path(package.source_dir)

        if package.skill_markdown_path and not Path(package.skill_markdown_path).exists():
            errors.append("Package skill markdown file is missing")

        if package.manifest_path and not Path(package.manifest_path).exists():
            errors.append("Package manifest.yaml is missing")

        if package.manifest_path and package_dir.exists():
            if package.format_version < 1:
                errors.append("format_version must be >= 1")

            reference_ids = [ref.id for ref in package.references if ref.id]
            if len(reference_ids) != len(set(reference_ids)):
                errors.append("Duplicate reference ids declared in manifest")

            script_ids = [script.id for script in package.scripts if script.id]
            if len(script_ids) != len(set(script_ids)):
                errors.append("Duplicate script ids declared in manifest")

            action_ids = [action.id for action in package.actions if action.id]
            if len(action_ids) != len(set(action_ids)):
                errors.append("Duplicate action ids declared in manifest")

            overlay_providers = [overlay.provider.strip().lower() for overlay in package.overlays if overlay.provider]
            overlay_keys = []
            for overlay in package.overlays:
                overlay_key = (
                    overlay.provider.strip().lower(),
                    (overlay.model or "").strip().lower(),
                    tuple(model.lower() for model in overlay.models),
                )
                overlay_keys.append(overlay_key)
            if len(overlay_keys) != len(set(overlay_keys)):
                errors.append("Duplicate overlay providers declared in manifest")

            seen_resource_paths = set()
            for ref in package.references:
                seen_resource_paths.add(ref.path)
                if not _path_exists(package_dir, ref.path):
                    errors.append(f"Declared reference path does not exist: {ref.path}")

            for script in package.scripts:
                seen_resource_paths.add(script.path)
                if not _path_exists(package_dir, script.path):
                    errors.append(f"Declared script path does not exist: {script.path}")

            for overlay in package.overlays:
                if not _path_exists(package_dir, overlay.path):
                    errors.append(f"Declared overlay path does not exist: {overlay.path}")
                else:
                    overlay_payload = _safe_overlay_dict(package_dir / overlay.path)
                    if overlay_payload is None:
                        errors.append(f"Declared overlay yaml is invalid: {overlay.path}")

            action_resource_ids = {
                resource.id: resource.path
                for resource in package.resources
                if resource.id
            }
            action_resource_paths = {
                resource.path
                for resource in package.resources
                if resource.path
            }
            for action in package.actions:
                if action.tool:
                    pass
                elif action.path:
                    if not _path_exists(package_dir, action.path):
                        errors.append(f"Declared action path does not exist: {action.path}")
                elif action.resource:
                    action_target_path = action_resource_ids.get(action.resource, action.resource)
                    if not _path_exists(package_dir, action_target_path):
                        errors.append(f"Declared action resource does not exist: {action.resource}")
                    elif action.resource not in action_resource_ids and action.resource not in action_resource_paths:
                        warnings.append(f"Action '{action.id}' references undeclared resource: {action.resource}")
                else:
                    warnings.append(f"Action '{action.id}' has no tool, resource, or path")

            for resource in package.resources:
                if resource.path and not _path_exists(package_dir, resource.path):
                    errors.append(f"Declared resource path does not exist: {resource.path}")

            undeclared_reference_paths = {
                ref.path for ref in SkillLoader._discover_reference_specs(package_dir)
            } - {ref.path for ref in package.references}
            undeclared_script_paths = {
                script.path for script in SkillLoader._discover_script_specs(package_dir)
            } - {script.path for script in package.scripts}
            undeclared_overlay_paths = {
                overlay.path for overlay in SkillLoader._discover_overlay_specs(package_dir)
            } - {overlay.path for overlay in package.overlays}

            if undeclared_reference_paths:
                warnings.append(
                    "Undeclared reference files discovered: " + ", ".join(sorted(undeclared_reference_paths))
                )
            if undeclared_script_paths:
                warnings.append(
                    "Undeclared script files discovered: " + ", ".join(sorted(undeclared_script_paths))
                )
            if undeclared_overlay_paths:
                warnings.append(
                    "Undeclared overlay files discovered: " + ", ".join(sorted(undeclared_overlay_paths))
                )

        return SkillValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class SkillValidator:
    """
    Schema and policy validation for skills.
    """

    @staticmethod
    def validate(skill: SkillSpec) -> SkillValidationResult:
        errors = []
        warnings = []

        if not skill.name:
            errors.append("Skill name is required")
        if not skill.version:
            errors.append("Skill version is required")
        if not skill.entrypoint:
            errors.append("Skill entrypoint is required")

        entrypoint_attr = skill.entrypoint.lower().replace(" ", "_")
        if not getattr(skill, entrypoint_attr, None):
            errors.append(f"Entrypoint section '{skill.entrypoint}' not found in Markdown")

        if skill.system_prompt and len(skill.system_prompt.strip()) < 10:
            warnings.append("System prompt is very short")

        if skill.inputs_schema is not None and not isinstance(skill.inputs_schema, dict):
            errors.append("inputs_schema must be a dictionary")
        if skill.outputs_schema is not None and not isinstance(skill.outputs_schema, dict):
            errors.append("outputs_schema must be a dictionary")

        if skill.constraints and skill.constraints.allowed_tools is not None:
            if not isinstance(skill.constraints.allowed_tools, list):
                errors.append("constraints.allowed_tools must be a list")
            else:
                for tool in skill.constraints.allowed_tools:
                    if not isinstance(tool, str):
                        errors.append(f"Invalid tool name in allowed_tools: {tool}")

        return SkillValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
