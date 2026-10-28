#!/usr/bin/env python3
"""Exercise work-case oracles and the synthetic backend, without model calls."""
import contextlib
import http.client
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / ".claude/evals/work"


class WorkCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.workspace = self.base / "workspace"
        self.app = self.workspace / "apps/app"

    def tearDown(self):
        self.tmp.cleanup()

    def fixture(self, name):
        shutil.copytree(WORK / "fixtures" / name, self.app)

    def grade(self, case):
        result = subprocess.run(
            [sys.executable, str(WORK / "externalgrade.py"), "--case", case,
             "--workspace", str(self.workspace)],
            capture_output=True, text=True, timeout=20,
        )
        value = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0 if value["status"] == "PASS" else 1)
        self.assertTrue(value["checks"])
        return value

    def test_seeded_failures_are_detected(self):
        self.fixture("staff")
        for case in ("field-repair", "batch-finish"):
            with self.subTest(case=case):
                self.assertEqual(self.grade(case)["status"], "FAIL")

    def test_candidate_cannot_replace_checks_with_incomplete_or_duplicate_claims(self):
        self.fixture("staff")
        cases = {
            "field-repair": ("fields.mjs", [
                "phone-leading-zeros-and-empty", "phone-cap-without-spurious-error",
                "account-character-contract", "manual-bank-independent-values", "full-phone-identity",
                "notices-require-known-basis", "optional-account-keeps-registration-valid",
            ]),
            "batch-finish": ("state.mjs", [
                "finish-one-current-entry", "finish-accumulated-on-untouched-next",
                "partial-next-entry-is-not-silently-dropped", "complete-next-entry-is-included",
                "empty-batch-is-not-submitted", "unknown-retry-preserves-exact-request",
                "completion-clears-only-confirmed-request",
            ]),
        }
        for case, (module, expected_ids) in cases.items():
            path = self.app / module
            original = path.read_text()
            for identifiers in (["worker-claim"], expected_ids[:-1],
                                expected_ids + [expected_ids[0]],
                                expected_ids[:-1] + [expected_ids[0]]):
                with self.subTest(case=case, identifiers=identifiers):
                    claims = [{"id": identifier, "status": "PASS", "detail": "No assertion ran."}
                              for identifier in identifiers]
                    path.write_text("console.log(" + json.dumps(json.dumps(claims)) + "); process.exit(0);\n")
                    result = self.grade(case)
                    self.assertEqual(result["status"], "FAIL")
                    self.assertEqual(result["checks"][0]["id"], "oracle-output")
            path.write_text(original)

    def test_refactor_baseline_and_changed_behavior(self):
        self.fixture("normalizer")
        self.assertEqual(self.grade("behavior-refactor")["status"], "PASS")
        path = self.app / "normalizer.mjs"
        original = path.read_text()
        path.write_text(original.replace(
            "value.id === undefined ? null : value.id", "value.id || null"))
        self.assertEqual(self.grade("behavior-refactor")["status"], "FAIL")
        path.write_text(original.replace(
            "value.id === undefined ? null : value.id",
            "value.id === undefined ? null : value.id === 0 ? false : value.id"))
        self.assertEqual(self.grade("behavior-refactor")["status"], "FAIL")

    def repair_fields(self):
        path = self.app / "fields.mjs"
        text = path.read_text()
        text = text.replace("String(Number(digits.slice(0, 4)))", "digits.slice(0, 4)")
        text = text.replace('digits.length > 4 ? "번호가 너무 길어요." : ""', '""')
        text = text.replace('return String(raw ?? ""); // account input',
                            'return String(raw ?? "").replace(/[^0-9]/g, ""); // account input')
        text = text.replace('bankName: bank === "other" ? draft.bankName : ""',
                            "bankName: draft.bankName")
        text = text.replace("return { ...draft, account: value };",
                            "return { ...draft, bankName: value };")
        text = text.replace("return draft.phoneLast;", "return draft.phonePrefix + draft.phoneMiddle + draft.phoneLast;")
        text = text.replace('if (draft.payType === "monthly" && amount < Number(defaults.hourlyRate) * 40 * 4)',
                            'if (false)')
        path.write_text(text)

    def repair_state(self):
        path = self.app / "state.mjs"
        text = path.read_text().replace(
            'if (isUntouched(state.current)) throw new Error("직원 정보를 입력해 주세요.");',
            'if (state.pending) return { ...state, phase: "saving", error: "" };')
        text = text.replace("const entries = [...state.rows, state.current];",
                            "const entries = isUntouched(state.current) ? [...state.rows] : [...state.rows, state.current];")
        path.write_text(text)

    def test_valid_field_repair_and_wrong_repairs(self):
        self.fixture("staff")
        self.repair_fields()
        self.assertEqual(self.grade("field-repair")["status"], "PASS")
        path = self.app / "fields.mjs"
        good = path.read_text()
        mutants = [
            ("digits.slice(0, 4)", "String(Number(digits.slice(0, 4)))"),
            ("return { ...draft, bankName: value };", "return { ...draft, account: value };"),
            ("if (false)", 'if (draft.payType === "monthly")'),
            ("return draft.phonePrefix + draft.phoneMiddle + draft.phoneLast;", "return draft.phoneLast;"),
        ]
        for before, after in mutants:
            with self.subTest(mutation=before):
                self.assertIn(before, good)
                path.write_text(good.replace(before, after))
                self.assertEqual(self.grade("field-repair")["status"], "FAIL")
        path.write_text(good)

    def test_valid_batch_repair_and_wrong_repairs(self):
        self.fixture("staff")
        self.repair_state()
        self.assertEqual(self.grade("batch-finish")["status"], "PASS")
        path = self.app / "state.mjs"
        good = path.read_text()
        mutants = [
            ('if (state.pending) return { ...state, phase: "saving", error: "" };', ""),
            ("isUntouched(state.current) ? [...state.rows]", "!state.current.phoneLast ? [...state.rows]"),
        ]
        for before, after in mutants:
            with self.subTest(mutation=before):
                self.assertIn(before, good)
                path.write_text(good.replace(before, after))
                self.assertEqual(self.grade("batch-finish")["status"], "FAIL")
        path.write_text(good)

    @contextlib.contextmanager
    def server(self, drop=False):
        db = self.base / "data.sqlite3"
        command = [sys.executable, str(WORK / "fixtures/staff/server.py"),
                   "--port", "0", "--db", str(db)]
        if drop:
            command.append("--drop-response-once")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
        try:
            # The server prints only after binding its ephemeral loopback port.
            import selectors
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(5), "server did not announce its URL")
            url = process.stdout.readline().strip()
            self.assertTrue(url.startswith("http://127.0.0.1:"), url)
            yield url, db
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)

    def request(self, url, data=None):
        req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.load(response)

    @staticmethod
    def batch():
        return {"request_id": "request-1", "entries": [
            {"name": "Sample A", "phonePrefix": "010", "phoneMiddle": "1234", "phoneLast": "0007",
             "payType": "hourly", "payAmount": "10000", "bank": "", "bankName": "", "account": ""}
        ]}

    def test_backend_replay_conflict_validation_and_fresh_read(self):
        with self.server() as (url, db):
            payload = self.batch()
            status, first = self.request(url + "/api/batches", payload)
            self.assertEqual(status, 201)
            status, replay = self.request(url + "/api/batches", payload)
            self.assertEqual((status, replay), (200, first))
            self.assertEqual(self.request(url + "/api/results/request-1")[1], first)
            rows = self.request(url + "/api/entries")[1]["entries"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["phoneLast"], "0007")
            changed = self.batch()
            changed["entries"][0]["name"] = "Changed"
            with self.assertRaises(urllib.error.HTTPError) as conflict:
                self.request(url + "/api/batches", changed)
            self.assertEqual(conflict.exception.code, 409)
            bad = self.batch()
            bad["request_id"] = "request-invalid"
            bad["entries"][0]["account"] = "abc"
            with self.assertRaises(urllib.error.HTTPError) as invalid:
                self.request(url + "/api/batches", bad)
            self.assertEqual(invalid.exception.code, 400)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM entries").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT count(*) FROM batches").fetchone()[0], 1)

    def test_lost_response_is_queryable_and_retry_does_not_duplicate(self):
        with self.server(drop=True) as (url, db):
            with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError, urllib.error.URLError)):
                self.request(url + "/api/batches", self.batch())
            saved = self.request(url + "/api/results/request-1")[1]
            self.assertEqual(saved["count"], 1)
            self.assertEqual(self.request(url + "/api/batches", self.batch())[1], saved)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM entries").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
