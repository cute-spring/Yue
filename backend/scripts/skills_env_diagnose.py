import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from app.services.skill_service import SkillDirectoryResolver, SkillRegistry


def _is_writable(path: Path) -> bool:
    if not path.exists():
        return False
    return os.access(path, os.W_OK)


def run_diagnose() -> dict:
    resolver = SkillDirectoryResolver()
    layered_dirs = resolver.resolve()
    registry = SkillRegistry()
    registry.set_layered_skill_dirs(layered_dirs)
    registry.load_all()

    dir_stats = []
    for item in layered_dirs:
        path = Path(item.path)
        dir_stats.append({
            "layer": item.layer,
            "path": str(path),
            "exists": path.exists(),
            "readable": os.access(path, os.R_OK) if path.exists() else False,
            "writable": _is_writable(path),
        })

    all_skills = registry.list_skills()
    counter = Counter(skill.source_layer or "unknown" for skill in all_skills)
    conflict_counter = Counter()
    unavailable_reasons = defaultdict(int)
    for skill in all_skills:
        if skill.override_from:
            conflict_counter[skill.override_from] += 1
        if skill.availability is False:
            missing = skill.missing_requirements or {}
            for reason in missing:
                unavailable_reasons[reason] += 1

    return {
        "directories": dir_stats,
        "skill_count": len(all_skills),
        "skill_count_by_layer": dict(counter),
        "override_count": sum(conflict_counter.values()),
        "override_sources": dict(conflict_counter),
        "unavailable_reason_count": dict(unavailable_reasons),
    }


def main() -> int:
    print(json.dumps(run_diagnose(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
