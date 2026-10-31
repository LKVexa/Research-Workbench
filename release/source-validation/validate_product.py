"""Black-box acceptance of an immutable Local Component Workbench package.

No product or foundation modules are imported. Every product action goes
through a fresh interpreter and the packaged workbench.py CLI.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import uuid

TEST_ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root):
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class Acceptance:
    def __init__(self, candidate):
        self.candidate = candidate.resolve()
        self.started = dt.datetime.now(dt.timezone.utc).isoformat()
        self.evidence = TEST_ROOT / "evidence" / ("a-" + uuid.uuid4().hex[:8])
        self.evidence.mkdir(parents=True)
        self.plan = read_json(TEST_ROOT / "ACCEPTANCE.json")
        self.original_snapshot = snapshot(self.candidate)
        expect("workbench.py" in self.original_snapshot, "Candidate lacks packaged CLI")
        self.package = self.evidence / "pkg spaces"
        shutil.copytree(self.candidate, self.package)
        expect(snapshot(self.package) == self.original_snapshot, "Relocated copy differs from candidate")
        self.state = self.evidence / "separate evidence state"
        self.calls = []
        self.checks = []
        self.data = {}

    def step(self, name, function):
        try:
            details = function()
            self.checks.append({"id": name, "status": "pass", "details": details})
        except Exception as exc:
            self.checks.append({"id": name, "status": "fail", "error": str(exc),
                                "traceback": traceback.format_exc()})

    def command(self, name, arguments, *, expected_exit=0, state=None, as_json=True, input_text=None):
        state = state or self.state
        argv = [sys.executable, "-I", "-B", str(self.package / "workbench.py"),
                "--state", str(state)]
        if as_json:
            argv.append("--json")
        argv.extend(arguments)
        start = dt.datetime.now(dt.timezone.utc).isoformat()
        proc = subprocess.run(argv, cwd=self.evidence, input=(input_text or "").encode(),
                              capture_output=True, timeout=120)
        number = len(self.calls) + 1
        prefix = f"{number:02d}-{name}"
        (self.evidence / (prefix + ".stdout.txt")).write_bytes(proc.stdout)
        (self.evidence / (prefix + ".stderr.txt")).write_bytes(proc.stderr)
        record = {"name": name, "argv": argv, "cwd": str(self.evidence), "started_at": start,
                  "exit_code": proc.returncode, "stdout_bytes": len(proc.stdout),
                  "stderr_bytes": len(proc.stderr),
                  "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
                  "stderr_sha256": hashlib.sha256(proc.stderr).hexdigest(),
                  "stdout_file": prefix + ".stdout.txt", "stderr_file": prefix + ".stderr.txt"}
        self.calls.append(record)
        expect(len(proc.stdout) <= self.plan["resource_bounds"]["captured_stdout_bytes"], "CLI stdout exceeded acceptance limit")
        expect(len(proc.stderr) <= self.plan["resource_bounds"]["captured_stderr_bytes"], "CLI stderr exceeded acceptance limit")
        expect(proc.returncode == expected_exit,
               f"{name}: exit {proc.returncode}, expected {expected_exit}; stdout={proc.stdout[:1500]!r}; stderr={proc.stderr[:1500]!r}")
        if not as_json:
            return {"stdout": proc.stdout.decode("utf-8", errors="replace"),
                    "stderr": proc.stderr.decode("utf-8", errors="replace")}
        value = json.loads(proc.stdout.decode("utf-8"))
        record["json_keys"] = sorted(value) if isinstance(value, dict) else None
        return value

    def doctor(self):
        value = self.command("doctor", ["doctor"])
        expect(value["status"] == "pass", "Setup checks failed")
        expect(all(c["status"] == "pass" for c in value["checks"]), "Doctor has nonpassing check")
        expect(any(c["id"] == "foundation_integrity" for c in value["checks"]), "Doctor omitted integrity")
        expect(Path(value["state_path"]).resolve() == self.state.resolve(), "State path not honored")
        self.data["doctor"] = value
        return value

    def catalog(self):
        value = self.command("catalog", ["catalog"])
        totals, records = value["totals"], value["components"]
        expected = self.plan["expected_catalog"]
        expect(totals["core_count"] == expected["core"], "Wrong core count")
        expect(totals["supporting_count"] == expected["supporting"], "Wrong supporting count")
        expect(len(records) == expected["total"], "Catalog omitted entries")
        expect(len({r["component_id"] for r in records}) == len(records), "Duplicate catalog IDs")
        core = [r for r in records if r["role"] == "core"]
        expect(dict(Counter(r["original_status"] for r in core)) == expected["core_statuses"], "Original core statuses changed")
        expect(all(r["original_g2"] == "fail" for r in core), "Original failed G2 changed")
        expect(all(r["scientific_validation"] == "unverified" for r in records), "Catalog inflates scientific validation")
        self.data["catalog"] = value
        return {"total": len(records), "totals": totals}

    def filters(self):
        enabled = self.command("enabled", ["catalog", "--executable"])["components"]
        actual = {r["component_id"]: r["cases"] for r in enabled}
        expect(actual == self.plan["expected_capabilities"], "Executable profile differs from frozen acceptance")
        expect(all(r["executable"] for r in enabled), "Executable filter includes disabled record")
        query = self.command("query", ["catalog", "--query", "D0007/C0322"])["components"]
        expect({r["component_id"] for r in query} == {"D0007/C0322-01", "D0007/C0322-02"}, "Query filter failed")
        supporting = self.command("supporting", ["catalog", "--collection", "TOPIC"])["components"]
        expect(len(supporting) == 16 and all(r["collection"] == "TOPIC" for r in supporting), "TOPIC filter failed")
        return actual

    def disabled(self):
        for component in self.plan["disabled_controls"]:
            value = self.command("disabled-" + component.replace("/", "-"), ["run", component], expected_exit=2)
            expect(value["status"] == "error" and "not executable" in value["error"], "Disabled capability was not rejected explicitly")

    def adapters(self):
        for name, component, case, accepted in (
            ("python", "D0001/C0081-03", "baseline", True),
            ("correct", "D0007/C0322-02", "correct", True),
            ("regression", "D0007/C0322-02", "regression", False),
        ):
            value = self.command(name, ["run", component, "--case", case])
            expect(value["execution"] == value["verification"] == "pass", "Fresh adapter execution failed")
            expect(value["scientific_validation"] == "unverified", "Fixture run inflates scientific claim")
            expect(value["candidate_accepted"] is accepted, "Candidate acceptance differs from control expectation")
            expect(value["check_counts"]["fail"] == 0 and value["check_counts"]["pass"] > 0, "Diagnostic checks failed")
            expect((self.state / "runs" / value["run_id"] / "stdout.log").is_file(), "No actual process stdout evidence")
            self.data[name] = value
        return {name: self.data[name] for name in ("python", "correct", "regression")}

    def verification(self):
        old = self.data["python"]["run_id"]
        count = len(list((self.state / "runs").iterdir()))
        value = self.command("verify", ["verify", old])
        expect(value["integrity"] == "pass" and value["state"] == "completed", "Saved run integrity failed")
        expect(len(list((self.state / "runs").iterdir())) == count, "Integrity-only verify unexpectedly executed")
        fresh = self.command("fresh", ["verify", old, "--fresh"])["fresh_run"]
        expect(fresh["run_id"] != old and fresh["verification"] == "pass", "Fresh verification did not make new passing attempt")
        old_payload = read_json(self.state / "runs" / old / "adapter-result.json")
        new_payload = read_json(self.state / "runs" / fresh["run_id"] / "adapter-result.json")
        expect(old_payload == new_payload, "Fresh deterministic payload differs")
        request = read_json(self.state / "runs" / fresh["run_id"] / "request.json")
        expect(request["parent_run_id"] == old, "Fresh verification lost lineage")
        all_runs = self.command("verify-all", ["verify"])
        expect(all_runs["status"] == "pass", "Batch integrity verification failed")
        self.data["fresh"] = fresh
        return fresh

    def resume(self):
        # A fault-injection fixture representing a committed request followed by
        # process death before result creation. It is not claimed as execution.
        template = read_json(self.state / "runs" / self.data["python"]["run_id"] / "request.json")
        run_id = "interrupted-" + uuid.uuid4().hex[:16]
        path = self.state / "runs" / run_id
        request = {**template, "run_id": run_id, "parent_run_id": None}
        write_json(path / "request.json", request)
        write_json(path / "request.sha256.json", {"sha256": sha(path / "request.json")})
        original = snapshot(path)
        before = self.command("verify-interrupted", ["verify", run_id], expected_exit=1)
        expect(before["integrity"] == "incomplete", "Interrupted request was treated as successful")
        resumed = self.command("resume", ["resume", run_id])
        expect(resumed["run_id"] != run_id and resumed["verification"] == "pass", "Resume did not execute a linked passing attempt")
        child_request = read_json(self.state / "runs" / resumed["run_id"] / "request.json")
        expect(child_request["parent_run_id"] == run_id, "Resume lost parent relation")
        count = len(list((self.state / "runs").iterdir()))
        reused = self.command("resume-again", ["resume", run_id])
        expect(reused["resume_reused"] is True and reused["run_id"] == resumed["run_id"], "Repeat resume did not reuse child")
        expect(len(list((self.state / "runs").iterdir())) == count, "Repeat resume duplicated execution")
        expect(all(sha(path / name) == value for name, value in original.items()), "Resume changed original request evidence")
        self.data["interrupted"] = run_id
        return {"parent": run_id, "child": resumed["run_id"]}

    def report(self):
        value = self.command("report", ["report"])
        expect(value["status"] == "created", "Report not created")
        html_path, json_path = Path(value["html_path"]), Path(value["json_path"])
        expect(html_path.resolve().is_relative_to(self.state.resolve()), "Report escaped state root")
        document = html_path.read_text(encoding="utf-8")
        data = read_json(json_path)
        expect(data["totals"]["core_count"] == 377 and len(data["catalog"]) == 393, "Report omitted catalog")
        expect("fixture" in document.lower() and "G2" in document and "209" in document, "Report omitted scientific boundaries")
        expect("paper-scale replication" in document, "Report lacks paper-scale limitation")
        expect("../../runs/" in document and "result.json" in document, "HTML lacks retained evidence links")
        regression = next(r for r in data["runs"] if r["run_id"] == self.data["regression"]["run_id"])
        expect(regression["candidate_accepted"] is False and regression["verification"] == "pass", "Report conflates diagnostic and candidate results")
        self.data["report"] = value
        return value

    def corrupt_report(self):
        # Change only a disposable copy of the generated run state.
        damaged = self.evidence / "damaged state"
        shutil.copytree(self.state, damaged)
        sidecar = damaged / "runs" / self.data["python"]["run_id"] / "request.sha256.json"
        content = read_json(sidecar)
        hostile_key = "<img src=x onerror=alert(1)>"
        content[hostile_key] = "fault injection"
        write_json(sidecar, content)
        value = self.command("corrupt-report", ["report"], state=damaged)
        expect(value["status"] == "created" and value["evidence_integrity"] == "fail", "Malformed evidence aborted or passed report")
        doc = Path(value["html_path"]).read_text(encoding="utf-8")
        data = read_json(Path(value["json_path"]))
        errors = [r for r in data["runs"] if r["integrity"] == "fail"]
        expect(any(hostile_key in r.get("error", "") for r in errors), "Fault did not reach report's hostile error-text path")
        expect(hostile_key not in doc and "&lt;img src=x onerror=alert(1)&gt;" in doc, "HTML error text was not escaped")
        result = self.command("corrupt-verify", ["verify"], state=damaged, expected_exit=1)
        expect(result["status"] == "fail", "Batch verify failed to report malformed evidence")
        return {"html_path": value["html_path"], "failed_rows": len(errors)}

    def arguments(self):
        for name, args in (
            ("invalid-case", ["run", "D0001/C0081-03", "--case", "baseline; echo nope"]),
            ("unknown-component", ["run", "D9999/UNKNOWN-01"]),
            ("invalid-timeout", ["run", "D0001/C0081-03", "--timeout", "-1"]),
            ("fresh-no-id", ["verify", "--fresh"]),
        ):
            value = self.command(name, args, expected_exit=2)
            expect(value["status"] == "error", "Invalid invocation lacks structured error")
        self.command("unknown-command", ["unknown-command"], as_json=False, expected_exit=2)

    def protected_paths(self):
        # verify on an existing protected root is read-only even if the guard
        # regresses: it attempts to read a deliberately absent run, not create one.
        for name, state in (("package-state", self.package), ("original-state", Path("D:/Deliverables/product-work/D0001"))):
            expect(state.is_dir(), "Protected-root rejection test requires existing root")
            value = self.command(name, ["verify", "nonexistent-test-run"], state=state, expected_exit=2)
            expect(value["status"] == "error" and "protected" in value["error"].lower(), "State protection not enforced")

    def menu(self):
        value = self.command("menu-default", [], as_json=False, input_text="0\n")
        expect("Local Component Workbench" in value["stdout"] and "Catalog" in value["stdout"], "Default guided interface missing")

    def unchanged(self):
        expect(snapshot(self.candidate) == self.original_snapshot, "Source candidate changed during validation")
        expect(snapshot(self.package) == self.original_snapshot, "Installed candidate changed during validation")
        return {"candidate_files": len(self.original_snapshot), "unchanged": True}

    def run(self):
        for name in ("doctor", "catalog", "filters", "disabled", "adapters", "verification", "resume",
                     "report", "corrupt_report", "arguments", "protected_paths", "menu", "unchanged"):
            self.step(name, getattr(self, name))
        report = {"schema_version": "1.0.0", "product": "local-component-workbench",
                  "candidate": str(self.candidate), "installed_copy": str(self.package),
                  "started_at_utc": self.started, "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "acceptance_plan_sha256": sha(TEST_ROOT / "ACCEPTANCE.json"),
                  "test_script_sha256": sha(Path(__file__)), "candidate_files": self.original_snapshot,
                  "commands": self.calls, "checks": self.checks,
                  "pass": all(c["status"] == "pass" for c in self.checks),
                  "test_evidence_root": str(self.evidence),
                  "implementation_imports": "none; every product action invokes the packaged CLI"}
        write_json(self.evidence / "REPORT.json", report)
        print(json.dumps({"pass": report["pass"], "checks": len(self.checks), "commands": len(self.calls),
                          "evidence": str(self.evidence),
                          "failures": [c for c in self.checks if c["status"] != "pass"]}, indent=2))
        return 0 if report["pass"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    return Acceptance(args.candidate).run()


if __name__ == "__main__":
    raise SystemExit(main())
