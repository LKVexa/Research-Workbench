"""Independent boundary and recovery tests using only disposable local fixtures.

Run with the supported Python: python -I -B tests/test_security.py.
These checks cover trusted pinned adapters; they do not assert containment for
arbitrary hostile programs.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FOUNDATION = Path(__file__).resolve().parents[1]
SOURCE = FOUNDATION / "src"
PACKAGE = Path(os.environ["FOUNDATION_TEST_PACKAGE"]).resolve() if os.environ.get("FOUNDATION_TEST_PACKAGE") else None
CODE_ROOT = PACKAGE if PACKAGE else SOURCE
SCHEMA_ROOT = PACKAGE / "schemas" if PACKAGE else FOUNDATION / "schemas"
sys.path.insert(0, str(CODE_ROOT))

from component_foundation.contracts import validate
from component_foundation.process import execute, Job
from component_foundation.runtime import Foundation
from component_foundation.safety import (
    FoundationError, RunLock, atomic_json, canonical, digest, inside,
    parse_json, prepare_state, read_json, sha256, valid_run_id,
)


def imported_module_identities():
    names = ("component_foundation", "component_foundation.contracts",
             "component_foundation.process", "component_foundation.runtime",
             "component_foundation.safety")
    records = {}
    for name in names:
        path = Path(sys.modules[name].__file__).resolve()
        records[name] = {"file": str(path),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "within_selected_code_root": path.is_relative_to(CODE_ROOT.resolve())}
    return records


class ImportBoundaryTests(unittest.TestCase):
    def test_imported_modules_belong_to_selected_code_root(self):
        for name, record in imported_module_identities().items():
            with self.subTest(module=name):
                self.assertTrue(record["within_selected_code_root"], record["file"])


class TemporaryCase(unittest.TestCase):
    def setUp(self):
        temp_root = FOUNDATION / "tests" / "work"
        temp_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="independent-", dir=temp_root)
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


class ParsingTests(TemporaryCase):
    def test_duplicate_keys_rejected_at_every_depth(self):
        for value in (b'{"status":"fail","status":"pass"}', b'{"a":{"x":1,"x":2}}'):
            with self.subTest(value=value), self.assertRaises(FoundationError):
                parse_json(value)

    def test_nonfinite_literals_and_overflow_rejected(self):
        for value in (b'NaN', b'Infinity', b'-Infinity', b'1e309', b'{"metric":-1e309}'):
            with self.subTest(value=value), self.assertRaises(FoundationError):
                parse_json(value)

    def test_size_and_nesting_limits(self):
        with self.assertRaises(FoundationError):
            parse_json(b'"1234567890"', limit=5)
        with self.assertRaises(FoundationError):
            parse_json(("[" * 42 + "0" + "]" * 42).encode())

    def test_schema_rejects_wrong_types_extra_fields_and_unsupported_vocabulary(self):
        schema = {"type": "object", "required": ["count", "status"],
                  "additionalProperties": False,
                  "properties": {"count": {"type": "integer", "minimum": 0},
                                 "status": {"type": "string", "enum": ["pass", "fail"]}}}
        validate({"count": 1, "status": "fail"}, schema)
        for value in ({"count": True, "status": "pass"}, {"status": "pass"},
                      {"count": -1, "status": "pass"},
                      {"count": 1, "status": "pass", "execute": "anything"}):
            with self.subTest(value=value), self.assertRaises(FoundationError):
                validate(value, schema)
        with self.assertRaises(FoundationError):
            validate(1, {"oneOf": [{"type": "integer"}]})

    def test_schema_rejects_direct_nonfinite_numbers(self):
        for value in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(FoundationError):
                validate(value, {"type": "number"})


class PathAndEvidenceTests(TemporaryCase):
    def test_traversal_and_absolute_paths_rejected(self):
        for name in ("../escape", "a/../../escape", "a/./b", "C:/escape", "/escape", "a\\b", "a:stream"):
            with self.subTest(name=name), self.assertRaises(FoundationError):
                inside(self.root, name)
        self.assertEqual(inside(self.root, "valid/nested.json"), self.root / "valid/nested.json")

    def test_protected_state_roots_rejected(self):
        package = self.root / "package"
        original = self.root / "original"
        package.mkdir()
        original.mkdir()
        for path in (package, package / "state", original, original / "state"):
            with self.subTest(path=path), self.assertRaises(FoundationError):
                prepare_state(path, package, [str(original)])
        self.assertEqual(prepare_state(self.root / "state", package, [str(original)]), self.root / "state")

    def test_invalid_run_ids_rejected(self):
        for run in ("../run", "a/b", "a:b", "UPPER", "a" * 65, ""):
            with self.subTest(run=run), self.assertRaises(FoundationError):
                valid_run_id(run)

    def test_atomic_immutable_write_retains_original_and_cleans_pending(self):
        path = self.root / "run.json"
        atomic_json(path, {"status": "fail"})
        old = path.read_bytes()
        with self.assertRaises(FoundationError):
            atomic_json(path, {"status": "pass"})
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(list(self.root.glob(".pending-*")), [])
        self.assertEqual(read_json(path), {"status": "fail"})

    def test_package_hash_tamper_and_unmanifested_shadow_rejected(self):
        package = self.root / "package"
        package.mkdir()
        payload = package / "payload.txt"
        payload.write_text("approved", encoding="utf-8")
        f = Foundation.__new__(Foundation)
        f.root = package
        f.manifest = {"files": {"payload.txt": sha256(payload)}}
        self.assertEqual(f.verify_package()["status"], "pass")
        payload.write_text("modified", encoding="utf-8")
        with self.assertRaises(FoundationError):
            f.verify_package()
        payload.write_text("approved", encoding="utf-8")
        (package / "shadow.py").write_text("# unexpected", encoding="utf-8")
        with self.assertRaises(FoundationError):
            f.verify_package()

    def test_parent_symlink_rejected_when_host_allows_creation(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("Host does not permit creating links for this check")
            shell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
            def literal(path):
                return "'" + str(path).replace("'", "''") + "'"
            command = "New-Item -ItemType Junction -Path " + literal(link) + " -Target " + literal(outside) + " -ErrorAction Stop | Out-Null"
            made = subprocess.run([str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
                                  capture_output=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if made.returncode != 0:
                self.skipTest("Host does not permit creating a junction for this check")
        try:
            with self.assertRaises(FoundationError):
                inside(self.root, "link/file.json")
        finally:
            # Remove only the link itself, never the target directory.
            os.rmdir(link)


@unittest.skipUnless(os.name == "nt", "Windows release process limits")
class ProcessTests(TemporaryCase):
    def call(self, code, **limits):
        return execute([sys.executable, "-I", "-B", "-c", code], self.root,
                       timeout=limits.pop("timeout", 3), **limits)

    def test_timeout_and_process_termination(self):
        result = self.call("import time; time.sleep(30)", timeout=0.15)
        self.assertEqual(result["outcome"], "timeout")
        self.assertLess(result["elapsed_seconds"], 5)

    def test_stdout_and_stderr_are_bounded(self):
        result = self.call("import sys; sys.stdout.buffer.write(b'x'*65536); sys.stderr.buffer.write(b'y'*65536)", max_output=4096)
        self.assertEqual(result["outcome"], "output_limit")
        self.assertLessEqual(len(result["stdout"]), 4096)
        self.assertLessEqual(len(result["stderr"]), 4096)

    def test_environment_does_not_forward_credential_like_variable(self):
        os.environ["FOUNDATION_TEST_PRIVATE_TOKEN"] = "synthetic-no-secret"
        try:
            result = self.call("import os; print('FOUNDATION_TEST_PRIVATE_TOKEN' in os.environ)")
        finally:
            del os.environ["FOUNDATION_TEST_PRIVATE_TOKEN"]
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"].strip(), b"False")

    def test_active_process_limit_blocks_children(self):
        code = "import subprocess,sys\ntry:\n subprocess.run([sys.executable,'-c','print(42)'],check=True)\n print('child-created')\nexcept OSError:\n print('child-blocked')"
        result = self.call(code)
        self.assertEqual(result["stdout"].strip(), b"child-blocked")

    def test_memory_limit_rejects_oversized_allocation(self):
        code = "try:\n x=bytearray(128*1024*1024)\n print('allocated')\nexcept MemoryError:\n print('memory-limited')"
        result = self.call(code, memory_mb=64)
        self.assertEqual(result["stdout"].strip(), b"memory-limited")

    def test_job_close_kills_its_process(self):
        proc = subprocess.Popen([sys.executable, "-I", "-B", "-c", "import time; time.sleep(30)"],
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            job = Job(proc)
            job.close()
            self.assertIsNotNone(proc.wait(timeout=5))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


class RecoveryTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.package = self.root / "protected" / "package"
        self.package.mkdir(parents=True)
        self.state = self.root / "state"
        self.run_id = "test-run"
        self.run_dir = self.state / "runs" / self.run_id
        self.run_dir.mkdir(parents=True)
        self.f = Foundation.__new__(Foundation)
        self.f.root = self.package
        self.f.config = {"protected_roots": []}
        self.f.manifest_digest = "a" * 64
        self.f.schemas = {name: read_json(SCHEMA_ROOT / (name + ".json"))
                          for name in ("request", "run-result")}
        self.request = {"schema_version": "1.0.0", "run_id": self.run_id,
                        "parent_run_id": None, "created_at": "2026-10-30T20:00:00+00:00",
                        "foundation_version": "0.1.0", "baseline_sha256": "b" * 64,
                        "component_id": "D0001/C0081-03", "case": "baseline", "timeout_seconds": 30,
                        "foundation_manifest_sha256": self.f.manifest_digest,
                        "python_sha256": sha256(Path(sys.executable))}
        validate(self.request, self.f.schemas["request"])
        atomic_json(self.run_dir / "request.json", self.request)
        atomic_json(self.run_dir / "request.sha256.json", {"sha256": sha256(self.run_dir / "request.json")})

    def test_interrupted_request_is_not_success(self):
        record = self.f.verify_run(self.state, self.run_id)
        self.assertEqual(record["integrity"], "incomplete")
        self.assertEqual(record["state"], "interrupted")

    def test_request_tampering_rejected(self):
        (self.run_dir / "request.json").write_bytes(canonical({**self.request, "case": "anything"}))
        with self.assertRaises(FoundationError):
            self.f.verify_run(self.state, self.run_id)

    def test_malformed_request_hash_sidecar_does_not_abort_report(self):
        atomic_json(self.run_dir / "request.sha256.json", [], replace=True)
        rows = self.f.runs(self.state)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["integrity"], "fail")

    def test_malformed_receipt_sidecar_does_not_abort_report(self):
        atomic_json(self.run_dir / "result.json", self.make_result())
        atomic_json(self.run_dir / "receipt.json", [])
        rows = self.f.runs(self.state)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["integrity"], "fail")

    def test_malformed_resume_marker_has_structured_failure(self):
        atomic_json(self.run_dir / "resume.json", [])
        with self.assertRaises(FoundationError):
            self.f.resume(self.state, self.run_id)

    def test_resume_creates_one_linked_child_then_reuses_it(self):
        calls = []
        def run(state, component, case, timeout, parent_run_id=None):
            calls.append(parent_run_id)
            return self.make_child()
        self.f.run = run
        first = self.f.resume(self.state, self.run_id)
        second = self.f.resume(self.state, self.run_id)
        self.assertEqual(first["run_id"], "child-run")
        self.assertTrue(second["resume_reused"])
        self.assertEqual(calls, [self.run_id])

    def test_completed_result_without_receipt_is_incomplete_not_unhandled_error(self):
        result = self.make_result()
        atomic_json(self.run_dir / "result.json", result)
        record = self.f.verify_run(self.state, self.run_id)
        self.assertEqual(record["integrity"], "incomplete")
        self.assertEqual(record["state"], "interrupted_commit")

    def make_child(self, run_id="child-run"):
        child = self.state / "runs" / run_id
        child.mkdir()
        request = {**self.request, "run_id": run_id, "parent_run_id": self.run_id}
        validate(request, self.f.schemas["request"])
        atomic_json(child / "request.json", request)
        atomic_json(child / "request.sha256.json", {"sha256": sha256(child / "request.json")})
        return {"run_id": run_id, "parent_run_id": self.run_id}

    def make_result(self):
        result = {"schema_version": "1.0.0", "run_id": self.run_id,
                  "component_id": self.request["component_id"], "case": self.request["case"],
                  "request_sha256": sha256(self.run_dir / "request.json"),
                  "foundation_manifest_sha256": self.f.manifest_digest,
                  "started_at": "2026-10-30T20:00:00+00:00", "finished_at": "2026-10-30T20:00:01+00:00",
                  "execution": "pass", "verification": "pass", "scientific_validation": "unverified",
                  "scope": "authored_fixture", "checks": [], "argv": [sys.executable], "artifacts": {}}
        validate(result, self.f.schemas["run-result"])
        return result

    def test_resume_after_result_commit_keeps_old_result_and_creates_new_attempt(self):
        result = self.make_result()
        atomic_json(self.run_dir / "result.json", result)
        original_bytes = (self.run_dir / "result.json").read_bytes()
        self.f.run = lambda *args, **kwargs: self.make_child()
        resumed = self.f.resume(self.state, self.run_id)
        self.assertEqual(resumed["parent_run_id"], self.run_id)
        self.assertEqual((self.run_dir / "result.json").read_bytes(), original_bytes)
        self.assertFalse((self.run_dir / "receipt.json").exists())

    def test_reserved_resume_recovers_existing_child_without_duplicate_execution(self):
        atomic_json(self.run_dir / "resume.json", {"status": "reserved", "created_at": "2026-10-30T20:00:00+00:00"})
        self.make_child()
        self.f.run = lambda *a, **k: self.fail("Existing child must not be executed twice")
        resumed = self.f.resume(self.state, self.run_id)
        self.assertEqual(resumed["run_id"], "child-run")
        self.assertTrue(resumed["resume_reused"])

    def test_reserved_resume_without_child_can_start_one_attempt(self):
        atomic_json(self.run_dir / "resume.json", {"status": "reserved", "created_at": "2026-10-30T20:00:00+00:00"})
        self.f.run = lambda *a, **k: self.make_child()
        resumed = self.f.resume(self.state, self.run_id)
        self.assertEqual(resumed["run_id"], "child-run")
        self.assertEqual(len(list((self.state / "runs").iterdir())), 2)

    def test_reserved_resume_rejects_tampered_child_request(self):
        atomic_json(self.run_dir / "resume.json", {"status": "reserved", "created_at": "2026-10-30T20:00:00+00:00"})
        self.make_child()
        child_request = self.state / "runs" / "child-run" / "request.json"
        child_request.write_bytes(child_request.read_bytes() + b" ")
        with self.assertRaises(FoundationError):
            self.f.resume(self.state, self.run_id)

    def test_linked_child_corrupted_profile_rejected_even_with_updated_digest(self):
        self.make_child()
        atomic_json(self.run_dir / "resume.json", {"status": "linked", "child_run_id": "child-run", "created_at": "2026-10-30T20:00:00+00:00"})
        child = self.state / "runs" / "child-run"
        request = read_json(child / "request.json")
        request["baseline_sha256"] = "c" * 64
        validate(request, self.f.schemas["request"])
        atomic_json(child / "request.json", request, replace=True)
        atomic_json(child / "request.sha256.json", {"sha256": sha256(child / "request.json")}, replace=True)
        with self.assertRaisesRegex(FoundationError, "profile mismatch"):
            self.f.resume(self.state, self.run_id)

    def test_linked_child_folder_identity_rejected(self):
        self.make_child()
        atomic_json(self.run_dir / "resume.json", {"status": "linked", "child_run_id": "child-run", "created_at": "2026-10-30T20:00:00+00:00"})
        child = self.state / "runs" / "child-run"
        request = read_json(child / "request.json")
        request["run_id"] = "different-child"
        atomic_json(child / "request.json", request, replace=True)
        atomic_json(child / "request.sha256.json", {"sha256": sha256(child / "request.json")}, replace=True)
        with self.assertRaisesRegex(FoundationError, "identity mismatch"):
            self.f.resume(self.state, self.run_id)

    def test_request_without_digest_has_explicit_interrupted_state_and_recovers(self):
        (self.run_dir / "request.sha256.json").unlink()
        request_bytes = (self.run_dir / "request.json").read_bytes()
        record = self.f.verify_run(self.state, self.run_id)
        self.assertEqual(record["integrity"], "incomplete")
        self.assertEqual(record["state"], "interrupted_request")
        self.f.run = lambda *a, **k: self.make_child()
        resumed = self.f.resume(self.state, self.run_id)
        self.assertEqual(resumed["parent_run_id"], self.run_id)
        self.assertEqual((self.run_dir / "request.json").read_bytes(), request_bytes)
        self.assertFalse((self.run_dir / "request.sha256.json").exists())
        recovery = read_json(self.run_dir / "recovery.json")
        self.assertEqual(recovery["observed_request_sha256"], sha256(self.run_dir / "request.json"))

    def test_reserved_child_without_digest_links_and_remains_incomplete(self):
        self.make_child()
        child = self.state / "runs" / "child-run"
        (child / "request.sha256.json").unlink()
        atomic_json(self.run_dir / "resume.json", {"status": "reserved", "created_at": "2026-10-30T20:00:00+00:00"})
        self.f.run = lambda *a, **k: self.fail("Existing incomplete child must not be duplicated")
        resumed = self.f.resume(self.state, self.run_id)
        self.assertTrue(resumed["resume_reused"])
        self.assertEqual(resumed["run_id"], "child-run")
        child_state = self.f.verify_run(self.state, "child-run")
        self.assertEqual(child_state["integrity"], "incomplete")
        self.assertEqual(child_state["state"], "interrupted_request")

    def test_lock_excludes_concurrent_resume_and_recovers_after_release(self):
        path = self.run_dir / "active.lock"
        with RunLock(path):
            with self.assertRaises(FoundationError):
                with RunLock(path):
                    pass
        with RunLock(path):
            pass


if __name__ == "__main__":
    run = unittest.main(verbosity=2, exit=False)
    print(json.dumps({"selected_code_root": str(CODE_ROOT.resolve()),
                      "selected_schema_root": str(SCHEMA_ROOT.resolve()),
                      "imported_modules": imported_module_identities()}, sort_keys=True))
    raise SystemExit(0 if run.result.wasSuccessful() else 1)
