import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestStage5RuntimeBoundaryHarness(unittest.TestCase):
    def test_runtime_boundary_harness_reports_pass_and_required_artifacts(self):
        backend_dir = Path(__file__).resolve().parents[1]
        workspace_root = backend_dir.parent
        result = subprocess.run(
            [
                "python",
                "scripts/skill_runtime_boundary_harness.py",
                "--workspace-root",
                str(workspace_root),
            ],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["harness"], "stage5-lite-runtime-boundary")
        checks = report["checks"]
        self.assertTrue(checks["activation_state_store"])
        self.assertTrue(checks["runtime_catalog_projector"])
        self.assertTrue(checks["visibility_resolver"])
        self.assertTrue(checks["tool_capability_provider"])
        self.assertTrue(checks["prompt_injection_adapter"])
        self.assertEqual(report["artifacts"]["visible_refs"], ["active-skill:1.0.0"])
        self.assertEqual(report["artifacts"]["effective_tools"], ["builtin:docs_read"])
        self.assertTrue(
            report["artifacts"]["composed_prompt"].startswith("Base prompt\n\n[Active Skill: active-skill]")
        )
        manifest = report["artifacts"]["externalization_manifest"]
        self.assertEqual(manifest["schema_version"], "stage5-lite-boundary-manifest/v1")
        self.assertEqual(manifest["stage"], "stage5-lite")
        self.assertEqual(manifest["mode"], "non-publishing")
        self.assertEqual(manifest["harness"], "stage5-lite-runtime-boundary")
        self.assertEqual(manifest["status"], "pass")
        self.assertEqual(
            manifest["boundary_ids"],
            [
                "activation_state_store",
                "prompt_injection_adapter",
                "runtime_catalog_projector",
                "tool_capability_provider",
                "visibility_resolver",
            ],
        )
        self.assertEqual(
            sorted(item["id"] for item in manifest["boundaries"]),
            manifest["boundary_ids"],
        )
        for item in manifest["boundaries"]:
            self.assertIn(item["id"], manifest["boundary_ids"])
            self.assertEqual(item["status"], "pass")
            self.assertIn("deterministic_evidence", item)
            self.assertIsInstance(item["deterministic_evidence"], dict)

    def test_runtime_boundary_harness_can_export_manifest_artifact(self):
        backend_dir = Path(__file__).resolve().parents[1]
        workspace_root = backend_dir.parent
        with tempfile.TemporaryDirectory(prefix="stage5-lite-manifest-test-") as td:
            manifest_path = Path(td) / "boundary_manifest.json"
            result = subprocess.run(
                [
                    "python",
                    "scripts/skill_runtime_boundary_harness.py",
                    "--workspace-root",
                    str(workspace_root),
                    "--manifest-out",
                    str(manifest_path),
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "stage5-lite-boundary-manifest/v1")
            self.assertEqual(manifest["status"], "pass")
            self.assertEqual(len(manifest["boundaries"]), len(manifest["boundary_ids"]))
            self.assertEqual(
                sorted(item["id"] for item in manifest["boundaries"]),
                manifest["boundary_ids"],
            )


if __name__ == "__main__":
    unittest.main()
