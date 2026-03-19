import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _default_agents_file() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "agents.json"


def _default_groups_file() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "skill_groups.json"


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def migrate(agents_file: Path, skill_groups_file: Path, dry_run: bool = False) -> Dict[str, Any]:
    agents = _load_json(agents_file, [])
    groups = _load_json(skill_groups_file, [])
    if not isinstance(agents, list):
        agents = []
    if not isinstance(groups, list):
        groups = []

    existing_group_ids = {str(group.get("id")) for group in groups if isinstance(group, dict)}
    generated_groups: List[Dict[str, Any]] = []
    migrated_count = 0

    for agent in agents:
        if not isinstance(agent, dict):
            continue
        skill_mode = str(agent.get("skill_mode") or "off")
        visible_skills = agent.get("visible_skills") if isinstance(agent.get("visible_skills"), list) else []
        previous_kind = agent.get("agent_kind")

        if skill_mode == "off":
            agent["agent_kind"] = "traditional"
        else:
            agent["agent_kind"] = "universal"

        if previous_kind != agent["agent_kind"]:
            migrated_count += 1

        if not isinstance(agent.get("skill_groups"), list):
            agent["skill_groups"] = []
        if not isinstance(agent.get("extra_visible_skills"), list):
            agent["extra_visible_skills"] = []
        if not isinstance(agent.get("resolved_visible_skills"), list):
            agent["resolved_visible_skills"] = list(visible_skills)

        if skill_mode != "off" and visible_skills:
            agent_id = str(agent.get("id") or "")
            legacy_group_id = f"legacy-group-{agent_id}" if agent_id else f"legacy-group-{len(generated_groups)+1}"
            if legacy_group_id not in existing_group_ids:
                group = {
                    "id": legacy_group_id,
                    "name": f"legacy-{agent.get('name') or legacy_group_id}",
                    "description": "Generated from legacy visible_skills during migration",
                    "skill_refs": visible_skills,
                }
                generated_groups.append(group)
                existing_group_ids.add(legacy_group_id)
            if legacy_group_id not in agent["skill_groups"]:
                agent["skill_groups"].append(legacy_group_id)

    migrated_groups = groups + generated_groups
    result = {
        "agents_file": str(agents_file),
        "skill_groups_file": str(skill_groups_file),
        "dry_run": dry_run,
        "migrated_agent_count": migrated_count,
        "generated_group_count": len(generated_groups),
        "status": "dry_run" if dry_run else "migrated",
    }

    if dry_run:
        return result

    _dump_json(agents_file, agents)
    _dump_json(skill_groups_file, migrated_groups)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents-file", default=str(_default_agents_file()))
    parser.add_argument("--skill-groups-file", default=str(_default_groups_file()))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = migrate(
        agents_file=Path(args.agents_file),
        skill_groups_file=Path(args.skill_groups_file),
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
