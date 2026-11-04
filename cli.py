#!/usr/bin/env python3
"""Inventory PVA components or execute a pinned, bounded local subset."""
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
LOCAL = (
    ("pva-docker-template", "scripts/verify_data.py", "31f2df536bf2e66171c8053811f8af52f8bb1a1fcecbeccb7faeb34356cf0b0a",
     "pva.csv-summary/v1", ("provenance_verified", "scientific_claims_validated", "network_used"), "completed_csv_summary"),
    ("pva-lean-bridge", "cli.py", "c749262ba6a0bb1d0d4084cb56e119aaf46157d7dcb1fdba6c538d95f856165c",
     "pva.formalization-backlog/v1", ("lean_compilation_executed", "original_claims_proved", "files_written"), "completed_backlog_extraction"),
    ("pva-ledger", "cli.py", "4b8948e5c99c53d3aec942506ea3b1f41fb60a9c127e4f2e2bc070baada219df",
     "pva.local-receipt/v1", ("authorship_verified", "network_used"), "completed_local_receipt"),
    ("pva-swarm", "app.py", "5ea9fc44b69c2fabbccedb6b7a02075ca0d3bfa3aafc00912ed64e0e316c238d",
     "pva.local-paper-registry/v1", ("distributed_validation_verified", "doi_resolution_checked"), "completed_registry_snapshot"),
)


def _run_pinned(source, arguments, expected_sha256, runner):
    if source.is_symlink() or not source.is_file():
        raise ValueError("bounded regular source required")
    with source.open("rb") as handle:
        code = handle.read(65537)
    if len(code) > 65536:
        raise ValueError("bounded regular source required")
    digest = hashlib.sha256(code).hexdigest()
    if digest != expected_sha256:
        raise ValueError("source digest diverged; review before updating the pin")
    bootstrap = "import sys;__file__=sys.argv.pop(1);exec(compile(sys.argv.pop(1),__file__,'exec'))"
    proc = runner([sys.executable, "-I", "-c", bootstrap, str(source), code.decode("utf-8"),
                   *arguments], capture_output=True, text=True, timeout=30,
                  env=SAFE_ENV.copy(), check=False)
    if proc.returncode != 0 or len(proc.stdout.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("process failed or exceeded output limit")
    report = json.loads(proc.stdout)
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    return report, digest


def inspect(workspace, target=None, run_lint=False, expected_sha256=LINT_SHA256,
            runner=subprocess.run, run_local=False):
    workspace = Path(workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("workspace must be a directory")
    steps = [{"component": name, "source_present": (workspace / name).is_dir(),
              "state": "discovered_not_executed" if (workspace / name).is_dir() else "missing"}
             for name in COMPONENTS]
    result = {"schema": "pva.pipeline-observation/v1", "steps": steps,
              "execution_status": "not_executed", "complete_pipeline_validated": False,
              "scientific_claims_validated": False, "external_service_calls": False,
              "docker_build_executed": False, "lean_compilation_executed": False,
              "external_publication_performed": False, "adversarial_validation_executed": False,
              "scope": "Pinned local structural scan, CSV summary, formalization backlog, content receipt and reported-paper snapshot only. Not the full scientific PVA pipeline."}
    if not run_lint and not run_local:
        return result
    if target is None:
        raise ValueError("--target is required with an execution mode")
    target = Path(target).resolve(strict=True)
    if not target.is_dir():
        raise ValueError("target must be a directory")
    source = workspace / "pva-lint" / "cli.py"
    report, digest = _run_pinned(source, ["--path", str(target), "--json"], expected_sha256, runner)
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
    if run_local:
        for i, (name, relative, pin, schema, false_flags, state) in enumerate(LOCAL, start=1):
            args = ["record", str(target / "README.md")] if name == "pva-ledger" else []
            if name == "pva-swarm":
                args = ["--snapshot"]
            try:
                report, digest = _run_pinned(workspace / name / relative, args, pin, runner)
                if report.get("schema") != schema or any(report.get(k) is not False for k in false_flags):
                    raise ValueError("schema or evidence scope changed")
                if name == "pva-ledger" and (report.get("external_publication") != "not_performed"
                                              or report.get("external_references") != []):
                    raise ValueError("external publication claim is outside this scope")
                steps[i].update(state=state, source_sha256=digest, report=report)
            except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
                steps[i]["state"] = "blocked"
                result["execution_status"] = "blocked_partial"
                result["blocked_component"] = name
                return result
        result["execution_status"] = "local_subset_completed"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--target", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run-lint", action="store_true")
    mode.add_argument("--run-local", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.workspace, args.target, args.run_lint, run_local=args.run_local)
    except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
        print("Blocked: source, process, schema or evidence scope could not be verified.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["execution_status"] == "blocked_partial" else 0


if __name__ == "__main__":
    raise SystemExit(main())
