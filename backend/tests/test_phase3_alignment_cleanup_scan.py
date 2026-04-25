import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestPhase3AlignmentCleanupScan(unittest.TestCase):
    def test_scan_reports_deprecated_alignment_markers_with_actions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
            (root / "backend" / "notes").mkdir(parents=True, exist_ok=True)
            (root / "node_modules").mkdir(parents=True, exist_ok=True)

            (root / "docs" / "plans" / "INDEX.md").write_text(
                "- [ ] **Phase 3: 标准对齐清理** (移除旧的多格式 / 创作平台叙事与产品假设)\n",
                encoding="utf-8",
            )
            (root / "backend" / "notes" / "cleanup.txt").write_text(
                "这里记录 deprecated path 迁移提醒。\n",
                encoding="utf-8",
            )
            (root / "backend" / "notes" / "ok.txt").write_text(
                "all clear\n",
                encoding="utf-8",
            )
            (root / "node_modules" / "skip.txt").write_text(
                "deprecated path should be ignored here too.\n",
                encoding="utf-8",
            )

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/standard_alignment_cleanup_scan.py",
                    "--root",
                    str(root),
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "warn")
            self.assertEqual(report["finding_count"], 2)
            self.assertEqual(report["scanned_file_count"], 3)
            self.assertEqual(report["marker_counts"]["标准对齐清理"], 1)
            self.assertEqual(report["marker_counts"]["deprecated path"], 1)
            markers = {item["marker"] for item in report["warnings"]}
            self.assertIn("标准对齐清理", markers)
            self.assertIn("deprecated path", markers)
            self.assertTrue(all(item["suggested_action"] for item in report["warnings"]))
            self.assertTrue(
                any(item["path"].endswith("docs/plans/INDEX.md") for item in report["warnings"])
            )
            self.assertTrue(
                any(item["path"].endswith("backend/notes/cleanup.txt") for item in report["warnings"])
            )
            self.assertFalse(
                any("node_modules" in item["path"] for item in report["warnings"])
            )

    def test_scan_returns_clean_status_when_no_markers_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "safe.txt").write_text("just a normal note\n", encoding="utf-8")

            backend_dir = Path(__file__).resolve().parents[1]
            result = subprocess.run(
                [
                    "python",
                    "scripts/standard_alignment_cleanup_scan.py",
                    "--root",
                    str(root),
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "clean")
            self.assertEqual(report["finding_count"], 0)
            self.assertEqual(report["marker_counts"], {})
            self.assertEqual(report["warnings"], [])


if __name__ == "__main__":
    unittest.main()
