"""CLI checks against disposable real files; no fake application-test success."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts/local_check.py"


class LocalCheckTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        dest = Path(tmp.name)
        manifest = json.loads((ROOT / "automation/retired-actions.json").read_text())
        paths = [e["archive"] for e in manifest["workflows"]]
        paths += [e["path"] for e in manifest["runtime_inputs"]]
        paths.append("automation/retired-actions.json")
        for path in paths:
            target = dest / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        return dest

    def run_check(self, root, *args):
        result = subprocess.run([sys.executable, str(CHECK), "--root", str(root), *args],
                                capture_output=True, text=True, timeout=15, check=False)
        return result.returncode, json.loads(result.stdout)

    def test_exact_retirement_has_distinct_unrun_runtime_state(self):
        code, receipt = self.run_check(self.fixture(), "--structure-only")
        self.assertEqual(code, 0)
        self.assertEqual(receipt["archived_workflows"], 45)
        self.assertEqual(receipt["active_workflows"], 0)
        self.assertEqual(receipt["runtime"], "NOT_RUN")

    def test_full_default_refuses_missing_runtime_evidence(self):
        code, receipt = self.run_check(self.fixture())
        self.assertEqual(code, 2)
        self.assertEqual(receipt["runtime"], "BLOCKED")
        self.assertTrue(any("not declared" in x for x in receipt["blockers"]))
        self.assertTrue(any("test corpus" in x for x in receipt["blockers"]))
        self.assertNotIn("commands", receipt)

    def test_restored_workflow_is_not_retired(self):
        root = self.fixture()
        path = root / ".github/workflows/restored.yml"
        path.parent.mkdir(parents=True)
        path.write_text("on: push\njobs: {}\n")
        code, receipt = self.run_check(root, "--structure-only")
        self.assertEqual(code, 1)
        self.assertEqual(receipt["structure"], "FAIL")

    def test_changed_archive_is_not_preserved(self):
        root = self.fixture()
        path = next((root / "automation/archived-workflows").glob("*.yml"))
        path.write_text(path.read_text() + "\n# altered\n")
        self.assertEqual(self.run_check(root, "--structure-only")[0], 1)

    def test_changed_runtime_source_requires_requalification(self):
        root = self.fixture()
        (root / "src/index.ts").write_text("export default {};\n")
        self.assertEqual(self.run_check(root, "--structure-only")[0], 1)

    def test_missing_archive_is_failure(self):
        root = self.fixture()
        next((root / "automation/archived-workflows").glob("*.yml")).unlink()
        self.assertEqual(self.run_check(root, "--structure-only")[0], 1)

    def test_manifest_cannot_read_an_outside_path(self):
        root = self.fixture()
        path = root / "automation/retired-actions.json"
        manifest = json.loads(path.read_text())
        manifest["runtime_inputs"][0]["path"] = "../outside"
        path.write_text(json.dumps(manifest))
        self.assertEqual(self.run_check(root, "--structure-only")[0], 1)


if __name__ == "__main__":
    unittest.main()
