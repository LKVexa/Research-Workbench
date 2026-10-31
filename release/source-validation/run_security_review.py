"""Capture the independent security suite against an explicit package or source."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent


def hashes(code_root, schema_root):
    paths = list((code_root / "component_foundation").glob("*.py")) + list(schema_root.glob("*.json"))
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    foundation = ROOT.parent
    code_root = args.package.resolve() if args.package else foundation / "src"
    schema_root = args.package.resolve() / "schemas" if args.package else foundation / "schemas"
    evidence = ROOT / "evidence" / ("security-" + uuid.uuid4().hex)
    evidence.mkdir(parents=True)
    before = hashes(code_root, schema_root)
    env = dict(os.environ)
    if args.package:
        env["FOUNDATION_TEST_PACKAGE"] = str(args.package.resolve())
    else:
        env.pop("FOUNDATION_TEST_PACKAGE", None)
    command = [sys.executable, "-I", "-B", str(ROOT / "test_security.py")]
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=60)
    after = hashes(code_root, schema_root)
    (evidence / "stdout.txt").write_bytes(proc.stdout)
    (evidence / "stderr.txt").write_bytes(proc.stderr)
    text = proc.stderr.decode("utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests", text)
    identity = json.loads(proc.stdout.decode("utf-8").strip()) if proc.stdout.strip() else {}
    imported = identity.get("imported_modules", {})
    import_boundary = bool(imported) and all(
        record["within_selected_code_root"] and before.get(record["file"]) == record["sha256"]
        for record in imported.values()
    )
    report = {
        "review": "Independent foundation security and recovery tests",
        "executed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": command, "cwd": str(ROOT), "code_root": str(code_root),
        "schema_root": str(schema_root), "exit_code": proc.returncode,
        "tests_run": int(match.group(1)) if match else None,
        "imported_modules": imported, "import_boundary_verified": import_boundary,
        "files_before": before, "files_after": after, "tested_files_stable": before == after,
        "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr).hexdigest(),
        "test_source_sha256": hashlib.sha256((ROOT / "test_security.py").read_bytes()).hexdigest(),
        "pass": proc.returncode == 0 and before == after and import_boundary,
        "evidence_dir": str(evidence),
    }
    (evidence / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("pass", "exit_code", "tests_run", "tested_files_stable", "import_boundary_verified", "evidence_dir")}, indent=2))
    if proc.returncode:
        print(text)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
