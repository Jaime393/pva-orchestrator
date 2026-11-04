#!/usr/bin/env python3
"""Inventory PVA components; optionally run one pinned offline artifact scan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

COMPONENTS = ("pva-lint", "pva-docker-template", "pva-lean-bridge", "pva-ledger", "pva-swarm")
LINT_SHA256 = "ce06c19170547daa2f07f32003ba0673736e5cccd27c0b18066fd27f57b941b1"
SAFE_ENV = {"PATH": os.defpath, "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}


def inspect(workspace, target=None, run_lint=False, expected_sha256=LINT_SHA256,
            runner=subprocess.run):
    workspace = Path(workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("workspace must be a directory")
    steps = [{"component": name, "source_present": (workspace / name).is_dir(),
              "state": "discovered_not_executed" if (workspace / name).is_dir() else "missing"}
             for name in COMPONENTS]
    result = {"schema": "pva.pipeline-observation/v1", "steps": steps,
              "execution_status": "not_executed", "complete_pipeline_validated": False,
              "scientific_claims_validated": False, "external_service_calls": False,
              "scope": "Directory discovery plus optional pinned offline lint only; no Docker, Lean, ledger, swarm or model execution."}
    if not run_lint:
        return result
    if target is None:
        raise ValueError("--target is required with --run-lint")
    target = Path(target).resolve(strict=True)
    if not target.is_dir():
        raise ValueError("target must be a directory")
    source = workspace / "pva-lint" / "cli.py"
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 65536:
        raise ValueError("bounded regular lint source required")
    code = source.read_bytes()
    digest = hashlib.sha256(code).hexdigest()
    if digest != expected_sha256:
        raise ValueError("lint source digest diverged; review source before updating the pin")
    # Execute the exact reviewed bytes, not a file that could change after hashing.
    proc = runner([sys.executable, "-I", "-c", code.decode("utf-8"),
                   "--path", str(target), "--json"], capture_output=True, text=True,
                  timeout=30, env=SAFE_ENV.copy(), check=False)
    if proc.returncode != 0 or len(proc.stdout.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("lint process failed or exceeded output limit")
    report = json.loads(proc.stdout)
    flags = ("public_access_verified", "reproduction_executed", "scientific_claims_validated", "network_used")
    if report.get("schema") != "pva.artifact-readiness/v1" or any(report.get(key) is not False for key in flags):
        raise ValueError("lint schema or evidence scope changed")
    checks = report.get("checks")
    if not isinstance(checks, dict) or set(checks) != {"doi", "datos", "codigo", "docker", "reproduce", "figuras"}:
        raise ValueError("lint checks changed")
    if any(item.get("state") not in {"observed", "missing"} for item in checks.values()):
        raise ValueError("invalid lint evidence state")
    steps[0].update(state="completed_structural_scan", source_sha256=digest, report=report)
    result["execution_status"] = "partial"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--run-lint", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.workspace, args.target, args.run_lint)
    except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
        print("Blocked: source, process, schema or evidence scope could not be verified.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
