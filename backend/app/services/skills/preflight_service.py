from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from app.services.skills.compatibility import SkillCompatibilityEvaluator
from app.services.skills.import_models import SkillPreflightRecord
from app.services.skills.import_store import SkillImportStore
from app.services.skills.models import SkillDirectorySpec
from app.services.skills.parsing import SkillLoader, SkillValidator
from app.services.skills.setup_service import SkillSetupService


class SkillPreflightService:
    def __init__(
        self,
        *,
        import_store: SkillImportStore | None = None,
        compatibility_evaluator: SkillCompatibilityEvaluator | None = None,
    ):
        self.import_store = import_store or SkillImportStore()
        self.compatibility_evaluator = compatibility_evaluator or SkillCompatibilityEvaluator()
        self.setup_service = SkillSetupService(import_store=self.import_store)

    def refresh(self, directories: Iterable[SkillDirectorySpec]) -> List[SkillPreflightRecord]:
        records: List[SkillPreflightRecord] = []
        for spec in directories:
            records.extend(self._scan_directory(spec))
        self.import_store.replace_preflight_records(records)
        return records

    def _scan_directory(self, spec: SkillDirectorySpec) -> List[SkillPreflightRecord]:
        root = Path(spec.path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return []

        candidates: List[Path] = []
        if (root / "SKILL.md").exists():
            candidates.append(root)
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "SKILL.md").exists():
                candidates.append(child)
            elif child.is_file() and child.suffix.lower() == ".md":
                candidates.append(child)

        records: List[SkillPreflightRecord] = []
        for candidate in candidates:
            records.append(self._build_preflight_record(candidate=candidate, layer=spec.layer))
        return records

    def _build_preflight_record(self, *, candidate: Path, layer: str) -> SkillPreflightRecord:
        fmt = SkillLoader.detect_format(candidate)
        if fmt == "package_directory":
            return self._build_from_package(candidate=candidate, layer=layer)
        return self._build_from_markdown(candidate=candidate, layer=layer)

    def _build_from_package(self, *, candidate: Path, layer: str) -> SkillPreflightRecord:
        package = SkillLoader.parse_package(candidate)
        fallback_ref = f"{candidate.name}:unknown"
        if package is None:
            return SkillPreflightRecord(
                skill_name=candidate.name,
                skill_version="unknown",
                skill_ref=fallback_ref,
                source_path=str(candidate),
                source_layer=layer,
                status="unavailable",
                issues=[f"Failed to parse skill package: {candidate}"],
                suggestions=["Check SKILL.md frontmatter and markdown section format."],
            )

        validation = SkillLoader.validate_package(package)
        if not validation.is_valid:
            return SkillPreflightRecord(
                skill_name=package.name,
                skill_version=package.version,
                skill_ref=f"{package.name}:{package.version}",
                source_path=str(candidate),
                source_layer=layer,
                status="unavailable",
                issues=list(validation.errors),
                warnings=list(validation.warnings),
                suggestions=["Fix manifest/resources validation errors, then restart preflight."],
            )

        compatibility = self.compatibility_evaluator.evaluate_package(package)
        setup_validation = self.setup_service.parse_install_setup(package.install) if package.install is not None else None
        setup_errors = list(setup_validation.errors) if setup_validation and not setup_validation.valid else []
        setup_capable = bool(setup_validation and setup_validation.valid and setup_validation.setup is not None)
        setup_runtime = setup_validation.setup.runtime if setup_validation and setup_validation.setup else None
        setup_commands = list(setup_validation.setup.commands) if setup_validation and setup_validation.setup else []
        setup_supported_runtimes = [setup_runtime] if setup_runtime else []
        package_fingerprint = None
        fingerprint_path = package.source_dir or package.manifest_path or package.skill_markdown_path
        if fingerprint_path:
            package_fingerprint = self.setup_service.compute_package_fingerprint(fingerprint_path)
        previous = self.import_store.get_preflight_record(f"{package.name}:{package.version}")
        prior_trust = "trusted" if previous and previous.package_fingerprint == package_fingerprint and previous.trust_status == "trusted" else "untrusted"
        prior_status = "available" if setup_capable and prior_trust == "trusted" else ("not_needed" if not setup_capable else "available")
        if previous and previous.package_fingerprint == package_fingerprint and previous.setup_status in {"running", "succeeded", "failed"}:
            prior_status = previous.setup_status
        if not setup_capable:
            prior_trust = "untrusted"
            prior_status = "not_needed"
        issues = list(compatibility.issues)
        issues.extend(setup_errors)
        suggestions = self._build_suggestions(compatibility)
        if setup_errors:
            suggestions.append("Fix manifest install.setup to use only python/node runtime and plain command strings.")

        asset_issues, asset_suggestions = self._evaluate_excalidraw_assets(package)
        issues.extend(asset_issues)
        suggestions.extend(asset_suggestions)

        status = "available" if compatibility.status == "compatible" and not asset_issues and not setup_errors else "needs_fix"
        return SkillPreflightRecord(
            skill_name=package.name,
            skill_version=package.version,
            skill_ref=f"{package.name}:{package.version}",
            source_path=str(candidate),
            source_layer=layer,
            status=status,
            issues=issues,
            suggestions=suggestions,
            missing_bins=list(compatibility.missing_bins),
            missing_env=list(compatibility.missing_env),
            unsupported_tools=list(compatibility.unsupported_tools),
            os_mismatch=list(compatibility.os_mismatch),
            setup_capable=setup_capable,
            setup_required=setup_capable,
            trust_status=prior_trust,
            setup_status=prior_status,
            setup_supported_runtimes=setup_supported_runtimes,
            setup_runtime=setup_runtime,
            isolated_env_path=self.setup_service.isolated_env_path_for(setup_runtime, str(candidate)) if setup_runtime else None,
            package_fingerprint=package_fingerprint,
            last_setup_commands=setup_commands,
            setup_last_error=previous.setup_last_error if previous and previous.package_fingerprint == package_fingerprint else None,
            last_setup_started_at=previous.last_setup_started_at if previous and previous.package_fingerprint == package_fingerprint else None,
            last_setup_finished_at=previous.last_setup_finished_at if previous and previous.package_fingerprint == package_fingerprint else None,
        )

    def _build_from_markdown(self, *, candidate: Path, layer: str) -> SkillPreflightRecord:
        skill = SkillLoader.parse_markdown(candidate.read_text(encoding="utf-8"), source_path=str(candidate))
        fallback_ref = f"{candidate.stem}:unknown"
        if skill is None:
            return SkillPreflightRecord(
                skill_name=candidate.stem,
                skill_version="unknown",
                skill_ref=fallback_ref,
                source_path=str(candidate),
                source_layer=layer,
                status="unavailable",
                issues=[f"Failed to parse markdown skill: {candidate}"],
                suggestions=["Check markdown frontmatter and required sections."],
            )

        validation = SkillValidator.validate(skill, mode="compat")
        if not validation.is_valid:
            return SkillPreflightRecord(
                skill_name=skill.name,
                skill_version=skill.version,
                skill_ref=f"{skill.name}:{skill.version}",
                source_path=str(candidate),
                source_layer=layer,
                status="unavailable",
                issues=list(validation.errors),
                warnings=list(validation.warnings),
                suggestions=["Fix skill schema errors, then restart preflight."],
            )

        compatibility = self.compatibility_evaluator.evaluate_skill(skill)
        status = "available" if compatibility.status == "compatible" else "needs_fix"
        return SkillPreflightRecord(
            skill_name=skill.name,
            skill_version=skill.version,
            skill_ref=f"{skill.name}:{skill.version}",
            source_path=str(candidate),
            source_layer=layer,
            status=status,
            warnings=list(validation.warnings),
            issues=list(compatibility.issues),
            suggestions=self._build_suggestions(compatibility),
            missing_bins=list(compatibility.missing_bins),
            missing_env=list(compatibility.missing_env),
            unsupported_tools=list(compatibility.unsupported_tools),
            os_mismatch=list(compatibility.os_mismatch),
        )

    @staticmethod
    def _build_suggestions(compatibility) -> List[str]:
        suggestions: List[str] = []
        for item in compatibility.missing_bins:
            suggestions.append(f"Install required binary: {item}")
        for item in compatibility.missing_env:
            suggestions.append(f"Set required environment variable: {item}")
        for item in compatibility.unsupported_tools:
            suggestions.append(f"Remove or replace unsupported tool: {item}")
        if compatibility.os_mismatch:
            suggestions.append("Switch to a supported OS or adjust skill os constraints.")
        return suggestions

    @staticmethod
    def _evaluate_excalidraw_assets(package) -> tuple[List[str], List[str]]:
        if package.name != "excalidraw-diagram-generator":
            return [], []

        source_dir = Path(package.source_dir)
        libraries_dir = source_dir / "libraries"
        issues: List[str] = []
        suggestions: List[str] = []

        split_cmd = (
            f"python {source_dir / 'scripts' / 'split-excalidraw-library.py'} "
            f"{libraries_dir / '<icon-set>'}/"
        )

        if not libraries_dir.exists() or not libraries_dir.is_dir():
            issues.append("Excalidraw icon libraries/ directory is missing.")
            suggestions.append(
                "Create libraries/<icon-set>/ and import a .excalidrawlib package, then run: "
                f"{split_cmd}"
            )
            return issues, suggestions

        library_dirs = sorted(
            child for child in libraries_dir.iterdir() if child.is_dir() and not child.name.startswith(".")
        )
        if not library_dirs:
            issues.append("Excalidraw libraries/ has no icon-set subdirectories.")
            suggestions.append(
                "Add an icon-set directory under libraries/ and run splitter for that directory: "
                f"{split_cmd}"
            )
            return issues, suggestions

        for library_dir in library_dirs:
            reference_path = library_dir / "reference.md"
            icons_dir = library_dir / "icons"
            icon_files = [item for item in icons_dir.iterdir() if item.is_file()] if icons_dir.is_dir() else []

            if not reference_path.exists() or not reference_path.is_file():
                issues.append(f"Excalidraw library '{library_dir.name}' is missing reference.md.")
                suggestions.append(
                    f"Generate metadata for '{library_dir.name}' by running: "
                    f"python {source_dir / 'scripts' / 'split-excalidraw-library.py'} {library_dir}/"
                )
            if not icons_dir.exists() or not icons_dir.is_dir() or not icon_files:
                issues.append(f"Excalidraw library '{library_dir.name}' has missing or empty icons/.")
                suggestions.append(
                    f"Rebuild icons for '{library_dir.name}' by running: "
                    f"python {source_dir / 'scripts' / 'split-excalidraw-library.py'} {library_dir}/"
                )

        return issues, suggestions
