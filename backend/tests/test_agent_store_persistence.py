import json
import os
import tempfile
import unittest


class TestAgentStorePersistence(unittest.TestCase):
    def test_migrate_legacy_agents_file(self):
        from app.services.agent_store import AgentStore, AgentConfig

        with tempfile.TemporaryDirectory() as td:
            legacy_dir = os.path.join(td, "legacy")
            new_dir = os.path.join(td, "new")
            os.makedirs(legacy_dir, exist_ok=True)

            custom = AgentConfig(name="Custom", system_prompt="x")
            legacy_path = os.path.join(legacy_dir, "agents.json")
            with open(legacy_path, "w") as f:
                json.dump([custom.model_dump(mode="json")], f, indent=2)

            store = AgentStore(data_dir=new_dir, legacy_data_dir=legacy_dir)
            agents = store.list_agents()
            ids = {a.id for a in agents}
            self.assertIn(custom.id, ids)
            self.assertIn("builtin-docs", ids)
            self.assertIn("builtin-local-docs", ids)

            self.assertTrue(os.path.exists(os.path.join(new_dir, "agents.json")))

    def test_recover_from_backup_when_agents_file_corrupt(self):
        from app.services.agent_store import AgentStore, AgentConfig

        with tempfile.TemporaryDirectory() as td:
            store = AgentStore(data_dir=td, legacy_data_dir=os.path.join(td, "legacy"))
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
            self.assertGreaterEqual(len(agents), 2)
            with open(agents_path, "r") as f:
                restored = json.load(f)
            self.assertTrue(isinstance(restored, list))
            self.assertGreaterEqual(len(restored), 2)

    def test_preserve_corrupt_file_when_no_backup(self):
        from app.services.agent_store import AgentStore

        with tempfile.TemporaryDirectory() as td:
            store = AgentStore(data_dir=td, legacy_data_dir=os.path.join(td, "legacy"))
            agents_path = os.path.join(td, "agents.json")
            bak_path = f"{agents_path}.bak"
            if os.path.exists(bak_path):
                os.remove(bak_path)

            with open(agents_path, "w") as f:
                f.write("{")

            agents = store.list_agents()
            self.assertGreaterEqual(len(agents), 2)

            corrupt_files = [p for p in os.listdir(td) if p.startswith("agents.json.corrupt.")]
            self.assertTrue(len(corrupt_files) >= 1)

            with open(agents_path, "r") as f:
                data = json.load(f)
            self.assertTrue(isinstance(data, list))


if __name__ == "__main__":
    unittest.main()

