#!/usr/bin/env python3
"""External behavioral oracle. A pass covers code contracts, never browser execution."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PRELUDE = r"""
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
const app = process.argv[1];
const checks = [];
function check(id, operation) {
  try {
    operation();
    checks.push({ id, status: "PASS", detail: "Observed expected behavior." });
  } catch (error) {
    checks.push({ id, status: "FAIL", detail: String(error.message).slice(0, 1200) });
  }
}
const load = (name) => import(pathToFileURL(join(app, name)).href);
"""

FIELD_CHECKS = r"""
const f = await load("fields.mjs");
check("phone-leading-zeros-and-empty", () => {
  assert.equal(f.phoneSegment("0007").value, "0007");
  assert.equal(f.phoneSegment("").value, "");
  assert.equal(Boolean(f.phoneSegment("0007").error), false);
});
check("phone-cap-without-spurious-error", () => {
  assert.equal(f.phoneSegment("12345").value, "1234");
  assert.equal(Boolean(f.phoneSegment("12345").error), false);
  assert.equal(f.phoneSegment("0a0-07").value, "0007");
});
check("account-character-contract", () => {
  assert.equal(f.accountDigits(" 00-12 A34 "), "001234");
  assert.equal(f.accountDigits(""), "");
  assert.equal(f.accountDigits("000123"), "000123");
});
check("manual-bank-independent-values", () => {
  const original = { ...f.emptyEmployee(), account: "001234", bankName: "Existing" };
  const manual = f.changeBank(original, "other");
  const changed = f.changeBankName(manual, "New provider");
  assert.equal(changed.bankName, "New provider");
  assert.equal(changed.account, "001234");
  assert.equal(original.bankName, "Existing");
  const switched = f.changeBank(f.changeBank(changed, "sample-a"), "other");
  assert.equal(switched.bankName, "New provider");
  assert.equal(switched.account, "001234");
});
check("full-phone-identity", () => {
  const first = { ...f.emptyEmployee(), name: "A", phoneMiddle: "1234", phoneLast: "0007" };
  const second = { ...first, name: "B", phoneMiddle: "5678" };
  assert.notEqual(f.phoneKey(first), f.phoneKey(second));
  assert.deepEqual(f.employeeErrors(second, [first]), []);
});
check("notices-require-known-basis", () => {
  assert.equal(Boolean(f.payNotice({ ...f.emptyEmployee(), payType: "monthly", payAmount: "100" })), false);
  assert.equal(Boolean(f.payNotice({ ...f.emptyEmployee(), payAmount: "100" }, { hourlyRate: "200" })), true);
  assert.equal(Boolean(f.payNotice({ ...f.emptyEmployee(), payAmount: "200" }, { hourlyRate: "200" })), false);
});
check("optional-account-keeps-registration-valid", () => {
  const row = { ...f.emptyEmployee(), name: "A", phoneMiddle: "1234", phoneLast: "0007" };
  assert.deepEqual(f.employeeErrors(row), []);
});
"""

FIELD_CHECK_IDS = (
    "phone-leading-zeros-and-empty", "phone-cap-without-spurious-error", "account-character-contract",
    "manual-bank-independent-values", "full-phone-identity", "notices-require-known-basis",
    "optional-account-keeps-registration-valid",
)

BATCH_CHECKS = r"""
const s = await load("state.mjs");
const f = await load("fields.mjs");
const row = (name, last) => ({ ...f.emptyEmployee(), name, phoneMiddle: "1234", phoneLast: last });
const a = row("A", "0007");
const b = row("B", "0008");
check("finish-one-current-entry", () => {
  const before = { ...s.emptyState(), current: a };
  const prepared = s.prepareSubmission(before, () => "one");
  assert.equal(prepared.phase, "saving");
  assert.deepEqual(prepared.pending, { request_id: "one", entries: [a] });
  assert.equal(before.pending, null);
});
check("finish-accumulated-on-untouched-next", () => {
  const before = { ...s.emptyState(), rows: [a, b] };
  const prepared = s.prepareSubmission(before, () => "two");
  assert.deepEqual(prepared.pending.entries, [a, b]);
  assert.deepEqual(before.current, f.emptyEmployee());
  assert.equal(before.pending, null);
});
check("partial-next-entry-is-not-silently-dropped", () => {
  const before = { ...s.emptyState(), rows: [a, b], current: { ...f.emptyEmployee(), name: "Unfinished" } };
  const snapshot = JSON.stringify(before);
  assert.throws(() => s.prepareSubmission(before, () => "partial"));
  assert.equal(JSON.stringify(before), snapshot);
});
check("complete-next-entry-is-included", () => {
  const third = row("C", "0009");
  const prepared = s.prepareSubmission({ ...s.emptyState(), rows: [a, b], current: third }, () => "three");
  assert.deepEqual(prepared.pending.entries, [a, b, third]);
});
check("empty-batch-is-not-submitted", () => {
  assert.throws(() => s.prepareSubmission(s.emptyState(), () => "empty"));
});
check("unknown-retry-preserves-exact-request", () => {
  const first = s.prepareSubmission({ ...s.emptyState(), current: a }, () => "stable");
  const unknown = s.markUnknown(first, "Response unavailable");
  const restored = JSON.parse(JSON.stringify(unknown));
  let allocated = 0;
  const retry = s.prepareSubmission(restored, () => { allocated += 1; return "replacement"; });
  assert.equal(allocated, 0);
  assert.equal(retry.phase, "saving");
  assert.deepEqual(retry.pending, first.pending);
  assert.deepEqual(restored.pending, first.pending);
});
check("completion-clears-only-confirmed-request", () => {
  const pending = s.prepareSubmission({ ...s.emptyState(), current: a }, () => "confirmed");
  assert.throws(() => s.completeSubmission(pending, { request_id: "different", count: 1, ids: [1] }));
  const done = s.completeSubmission(pending, { request_id: "confirmed", count: 1, ids: [1] });
  assert.equal(done.phase, "complete");
  assert.equal(done.pending, null);
  assert.deepEqual(done.rows, []);
  assert.deepEqual(done.current, f.emptyEmployee());
  assert.equal(done.result.count, 1);
});
"""

BATCH_CHECK_IDS = (
    "finish-one-current-entry", "finish-accumulated-on-untouched-next",
    "partial-next-entry-is-not-silently-dropped", "complete-next-entry-is-included",
    "empty-batch-is-not-submitted", "unknown-retry-preserves-exact-request",
    "completion-clears-only-confirmed-request",
)


def fail(identifier, detail):
    return {"id": identifier, "status": "FAIL", "detail": detail[:2000]}


def node_checks(app, body, expected_ids):
    result = subprocess.run(
        ["node", "--input-type=module", "-e", PRELUDE + body + "\nconsole.log(JSON.stringify(checks));", str(app)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15,
    )
    if result.returncode:
        return [fail("module-execution", result.stderr or "Node exited unsuccessfully.")]
    try:
        checks = json.loads(result.stdout)
        if not isinstance(checks, list) or not checks or any(
            not isinstance(item, dict) or item.get("status") not in ("PASS", "FAIL")
            or not isinstance(item.get("id"), str) or not isinstance(item.get("detail"), str)
            for item in checks
        ):
            raise ValueError("Invalid oracle output")
        identifiers = [item["id"] for item in checks]
        if (len(identifiers) != len(expected_ids) or len(set(identifiers)) != len(identifiers)
                or set(identifiers) != set(expected_ids)):
            raise ValueError("Oracle did not return each expected check exactly once")
        return checks
    except ValueError:
        return [fail("oracle-output", "Behavior execution did not return the expected check results.")]


def cli_checks(app):
    examples = [
        ('{"operation":"create","value":{}}',
         {"id": None, "name": "", "phone": "", "account": "", "active": True}),
        ('{"operation":"update","value":{}}', {}),
        ('{"operation":"create","value":{"id":0,"name":" A ","phone":"010-0000-0007","account":"00-123","active":false}}',
         {"id": 0, "name": "A", "phone": "01000000007", "account": "00123", "active": False}),
        ('{"operation":"update","value":{"id":"0007","name":null,"phone":0,"account":"","active":0}}',
         {"id": "0007", "name": "", "phone": "0", "account": "", "active": False}),
        ('{"operation":"create","value":{"id":"","name":0,"phone":null,"account":null,"active":null}}',
         {"id": "", "name": "0", "phone": "", "account": "", "active": False}),
        ('{"operation":"update","value":{"id":0}}', {"id": 0}),
        ('{"operation":"update","value":{"name":"  A B  ","ignored":"x"}}', {"name": "A B"}),
        ('{"operation":"create","value":null}', {"error": "object_required"}),
        ('{"operation":"update","value":[]}', {"error": "object_required"}),
        ('{"operation":"create","value":false}', {"error": "object_required"}),
        ('{"operation":"unknown","value":{}}', {"error": "operation_required"}),
        ('null', {"error": "operation_required"}),
        ('{"invalid', {"error": "invalid_json"}),
        ('{"operation":"update","value":{"phone":"000-7","active":"false"}}', {"phone": "0007", "active": True}),
    ]
    result = subprocess.run(
        ["node", str(app / "cli.mjs")],
        input="\n".join(line for line, _ in examples) + "\n\n",
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode:
        return [fail("cli-execution", result.stderr or "CLI exited unsuccessfully.")]
    try:
        actual = [json.loads(line) for line in result.stdout.splitlines()]
    except ValueError:
        return [fail("cli-output", "CLI output is not one JSON result per nonblank input.")]
    checks = []
    if len(actual) != len(examples):
        return [fail("cli-result-count", "Expected %d results, observed %d." % (len(examples), len(actual)))]
    for index, ((_, expected), observed) in enumerate(zip(examples, actual)):
        equal = json.dumps(observed, sort_keys=True) == json.dumps(expected, sort_keys=True)
        checks.append({"id": "cli-%02d" % (index + 1), "status": "PASS" if equal else "FAIL",
                       "detail": "Observed expected behavior." if equal else
                       "Expected %s; observed %s." % (json.dumps(expected), json.dumps(observed))})
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    app = args.workspace.resolve() / "apps/app"
    try:
        if args.case == "field-repair":
            checks = node_checks(app, FIELD_CHECKS, FIELD_CHECK_IDS)
        elif args.case == "batch-finish":
            checks = node_checks(app, BATCH_CHECKS, BATCH_CHECK_IDS)
        elif args.case == "behavior-refactor":
            checks = cli_checks(app)
        else:
            checks = [fail("case", "Unknown work case.")]
    except (OSError, subprocess.TimeoutExpired) as error:
        checks = [fail("execution", str(error))]
    status = "PASS" if checks and all(check["status"] == "PASS" for check in checks) else "FAIL"
    print(json.dumps({"status": status, "checks": checks}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
