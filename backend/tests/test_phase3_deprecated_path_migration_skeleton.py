import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestPhase3DeprecatedPathMigrationSkeleton(unittest.TestCase):
    def test_plan_reports_deprecated_paths_without_modifying_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "legacy" / "notes").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "notes").mkdir(parents=True, exist_ok=True)

            source_file = root / "legacy" / "notes" / "old.txt"
            target_file = root / "docs" / "notes" / "new.txt"
            source_file.write_text("legacy content\n", encoding="utf-8")
            target_file.write_text("existing target content\n", encoding="utf-8")

            manifest = root / "deprecated-paths.json"
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "deprecated_path": "legacy/notes/old.txt",
                            "replacement_path": "docs/notes/new.txt",
                            "label": "cleanup-notes",
                        },
                        {
                            "deprecated_path": "legacy/notes/missing.txt",
                            "replacement_path": "docs/notes/missing.txt",
                            "label": "missing-source",
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/deprecated_path_migration_skeleton.py",
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "warn")
            self.assertTrue(report["dry_run"])
            self.assertEqual(report["operation_mode"], "preview_only")
            self.assertEqual(report["planned_move_count"], 2)
            self.assertEqual(report["action_required_count"], 2)
            self.assertEqual(report["applied"], False)
            self.assertEqual(report["written_files"], [])

            planned = {item["deprecated_path"]: item for item in report["planned_moves"]}
            self.assertEqual(planned["legacy/notes/old.txt"]["state"], "target_exists")
            self.assertEqual(planned["legacy/notes/missing.txt"]["state"], "missing_source")
            self.assertEqual(planned["legacy/notes/old.txt"]["replacement_path"], "docs/notes/new.txt")
            self.assertTrue(all(item["next_step"] for item in report["planned_moves"]))

            self.assertEqual(source_file.read_text(encoding="utf-8"), "legacy content\n")
            self.assertEqual(target_file.read_text(encoding="utf-8"), "existing target content\n")

    def test_plan_marks_manifest_with_invalid_entry_as_warn(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = root / "deprecated-paths.json"
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "deprecated_path": "legacy/notes/old.txt",
                            "label": "missing-replacement",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/deprecated_path_migration_skeleton.py",
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "warn")
            self.assertEqual(report["invalid_entry_count"], 1)
            self.assertEqual(report["planned_move_count"], 1)
            self.assertEqual(report["action_required_count"], 1)
            self.assertEqual(report["operation_mode"], "preview_only")
            self.assertEqual(report["planned_moves"][0]["state"], "invalid_entry")
            self.assertTrue(report["planned_moves"][0]["next_step"])

    def test_plan_marks_all_pending_entries_ready_without_writing_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "legacy" / "notes").mkdir(parents=True, exist_ok=True)

            source_file = root / "legacy" / "notes" / "old.txt"
            source_file.write_text("legacy content\n", encoding="utf-8")

            manifest = root / "deprecated-paths.json"
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "deprecated_path": "legacy/notes/old.txt",
                            "replacement_path": "docs/notes/new.txt",
                            "label": "cleanup-notes",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/deprecated_path_migration_skeleton.py",
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["action_required_count"], 0)
            self.assertEqual(report["planned_move_count"], 1)
            self.assertEqual(report["planned_moves"][0]["state"], "pending")
            self.assertTrue(report["planned_moves"][0]["next_step"])
            self.assertEqual(source_file.read_text(encoding="utf-8"), "legacy content\n")


if __name__ == "__main__":
    unittest.main()
