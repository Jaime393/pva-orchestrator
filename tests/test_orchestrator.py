import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("orchestrator", ROOT / "cli.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def report():
    return {"schema": "pva.artifact-readiness/v1",
            "checks": {key: {"state": "missing"} for key in
                       ("doi", "datos", "codigo", "docker", "reproduce", "figuras")},
            "public_access_verified": False, "reproduction_executed": False,
            "scientific_claims_validated": False, "network_used": False}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        (self.workspace / "pva-lint").mkdir()
        self.source = self.workspace / "pva-lint/cli.py"
        self.source.write_text("# bounded fixture\n")
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def invoke(self, output=None, returncode=0):
        def runner(args, **kwargs):
            self.assertIn("-I", args)
            self.assertIn("-c", args)
            self.assertEqual(args[3], self.source.read_text())
            self.assertNotIn("MIU_API_KEY", kwargs["env"])
            self.assertNotIn("shell", kwargs)
            return SimpleNamespace(returncode=returncode, stdout=json.dumps(output or report()))
        return MODULE.inspect(self.workspace, self.workspace, True, self.digest, runner)

    def test_inventory_never_claims_execution(self):
        r = MODULE.inspect(self.workspace)
        self.assertEqual(r["execution_status"], "not_executed")
        self.assertEqual(r["steps"][0]["state"], "discovered_not_executed")
        self.assertFalse(r["complete_pipeline_validated"])

    def test_lint_only_is_partial(self):
        r = self.invoke()
        self.assertEqual(r["execution_status"], "partial")
        self.assertEqual(r["steps"][0]["state"], "completed_structural_scan")
        self.assertTrue(all(s["state"] == "missing" for s in r["steps"][1:]))

    def test_digest_divergence_blocks(self):
        with self.assertRaisesRegex(ValueError, "digest"):
            MODULE.inspect(self.workspace, self.workspace, True)

    def test_missing_target_blocks(self):
        with self.assertRaisesRegex(ValueError, "target"):
            MODULE.inspect(self.workspace, run_lint=True)

    def test_process_failure_blocks(self):
        with self.assertRaisesRegex(ValueError, "process"):
            self.invoke(returncode=1)

    def test_scientific_scope_escalation_blocks(self):
        bad = report()
        bad["scientific_claims_validated"] = True
        with self.assertRaisesRegex(ValueError, "scope"):
            self.invoke(bad)

    def test_unknown_checks_block(self):
        bad = report()
        bad["checks"] = {}
        with self.assertRaisesRegex(ValueError, "checks"):
            self.invoke(bad)

    def test_real_pinned_local_lint(self):
        source = ROOT.parent / "pva-lint/cli.py"
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != MODULE.LINT_SHA256:
            self.skipTest("Pinned sibling lint is required for this integration case")
        r = MODULE.inspect(ROOT.parent, ROOT.parent / "pva-lint", True)
        self.assertEqual(r["execution_status"], "partial")
        self.assertFalse(r["steps"][0]["report"]["network_used"])

    def test_cli_does_not_overwrite_dashboard(self):
        dashboard = ROOT / "pva_dashboard.json"
        before = dashboard.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / "cli.py"), "--workspace", str(self.workspace)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["execution_status"], "not_executed")
        self.assertEqual(dashboard.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
