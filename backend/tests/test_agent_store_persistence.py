import json
import os
import tempfile
import unittest
import subprocess
from pathlib import Path


class TestAgentStorePersistence(unittest.TestCase):
    def test_ignore_legacy_agents_file(self):
        from app.services.agent_store import AgentStore, AgentConfig

        with tempfile.TemporaryDirectory() as td:
            legacy_dir = os.path.join(td, "legacy")
            data_dir = os.path.join(td, "new")
            os.makedirs(legacy_dir, exist_ok=True)

            custom = AgentConfig(name="Custom", system_prompt="x")
            legacy_path = os.path.join(legacy_dir, "agents.json")
            with open(legacy_path, "w") as f:
                json.dump([custom.model_dump(mode="json")], f, indent=2)

            store = AgentStore(data_dir=data_dir)
            agents = store.list_agents()
            ids = {a.id for a in agents}
            self.assertNotIn(custom.id, ids)
            self.assertIn("builtin-docs", ids)
            self.assertIn("builtin-local-docs", ids)
            self.assertIn("builtin-excel-analyst", ids)
            self.assertIn("builtin-pdf-research", ids)
            self.assertIn("builtin-ppt-builder", ids)
            self.assertIn("builtin-action-lab", ids)
            self.assertIn("builtin-browser-operator", ids)

            self.assertTrue(os.path.exists(os.path.join(data_dir, "agents.json")))

    def test_recover_from_backup_when_agents_file_corrupt(self):
        from app.services.agent_store import AgentStore, AgentConfig

        with tempfile.TemporaryDirectory() as td:
            store = AgentStore(data_dir=td)
            store.create_agent(AgentConfig(name="Custom", system_prompt="x"))

            agents_path = os.path.join(td, "agents.json")
            bak_path = f"{agents_path}.bak"

            with open(agents_path, "r") as f:
                good_data = json.load(f)
            with open(bak_path, "w") as f:
                json.dump(good_data, f, indent=2)

            with open(agents_path, "w") as f:
                f.write("{")

            agents = store.list_agents()
            self.assertGreaterEqual(len(agents), 8)
            with open(agents_path, "r") as f:
                restored = json.load(f)
            self.assertTrue(isinstance(restored, list))
            self.assertGreaterEqual(len(restored), 8)

    def test_preserve_corrupt_file_when_no_backup(self):
        from app.services.agent_store import AgentStore

        with tempfile.TemporaryDirectory() as td:
            store = AgentStore(data_dir=td)
            agents_path = os.path.join(td, "agents.json")
            bak_path = f"{agents_path}.bak"
            if os.path.exists(bak_path):
                os.remove(bak_path)

            with open(agents_path, "w") as f:
                f.write("{")

            agents = store.list_agents()
            self.assertGreaterEqual(len(agents), 8)

            corrupt_files = [p for p in os.listdir(td) if p.startswith("agents.json.corrupt.")]
            self.assertTrue(len(corrupt_files) >= 1)

            with open(agents_path, "r") as f:
                data = json.load(f)
            self.assertTrue(isinstance(data, list))

    def test_migrate_agent_kind_groups_dry_run_report(self):
        with tempfile.TemporaryDirectory() as td:
            agents_file = os.path.join(td, "agents.json")
            groups_file = os.path.join(td, "skill_groups.json")
            with open(agents_file, "w") as f:
                json.dump(
                    [
                        {"id": "a-off", "name": "Off", "system_prompt": "x", "skill_mode": "off", "visible_skills": []},
                        {"id": "a-auto", "name": "Auto", "system_prompt": "x", "skill_mode": "auto", "visible_skills": ["planner:1.0.0"]},
                    ],
                    f,
                )

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/migrate_agents_to_agent_kind_groups.py",
                    "--agents-file",
                    agents_file,
                    "--skill-groups-file",
                    groups_file,
                    "--dry-run",
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn('"dry_run": true', result.stdout)
            self.assertFalse(os.path.exists(groups_file))

    def test_migrate_agent_kind_groups_apply(self):
        with tempfile.TemporaryDirectory() as td:
            agents_file = os.path.join(td, "agents.json")
            groups_file = os.path.join(td, "skill_groups.json")
            with open(agents_file, "w") as f:
                json.dump(
                    [
                        {"id": "a-off", "name": "Off", "system_prompt": "x", "skill_mode": "off", "visible_skills": []},
                        {"id": "a-manual", "name": "Manual", "system_prompt": "x", "skill_mode": "manual", "visible_skills": ["planner:1.0.0"]},
                    ],
                    f,
                )

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/migrate_agents_to_agent_kind_groups.py",
                    "--agents-file",
                    agents_file,
                    "--skill-groups-file",
                    groups_file,
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)

            with open(agents_file, "r") as f:
                migrated_agents = json.load(f)
            by_id = {item["id"]: item for item in migrated_agents}
            self.assertEqual(by_id["a-off"]["agent_kind"], "traditional")
            self.assertEqual(by_id["a-manual"]["agent_kind"], "universal")
            self.assertGreaterEqual(len(by_id["a-manual"]["skill_groups"]), 1)

            with open(groups_file, "r") as f:
                migrated_groups = json.load(f)
            self.assertEqual(len(migrated_groups), 1)
            self.assertEqual(migrated_groups[0]["skill_refs"], ["planner:1.0.0"])


if __name__ == "__main__":
    unittest.main()
