"""Interpret actual native reports; zero tests and all-skipped runs are not success."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .model import Invalid, git


def fresh(root: Path, specification: dict) -> None:
    """Remove only old untracked native report files inside the caller checkout."""
    pattern = specification.get("path", "")
    if not pattern:
        return
    if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise Invalid("Test reports must stay in the caller checkout")
    for old in root.glob(pattern):
        if not old.resolve().is_relative_to(root.resolve()) or old.is_symlink():
            raise Invalid("Test report path escapes the caller checkout")
        if old.is_file():
            if git(root, "ls-files", "--", str(old.relative_to(root))):
                raise Invalid("Do not remove tracked files as old test reports")
            old.unlink()


def tests(root: Path, specification: dict, log: Path) -> int:
    kind = specification.get("kind", "junit")
    pattern = specification.get("path", "")
    if kind in {"junit", "trx"}:
        files = sorted(root.glob(pattern))
        if not files or any(not p.is_file() or not p.resolve().is_relative_to(root.resolve()) for p in files):
            raise Invalid("Selected tests produced no contained report")
        total = 0
        for path in files:
            try:
                node = ET.parse(path).getroot()
            except ET.ParseError as error:
                raise Invalid(f"Malformed native XML test report: {path.name}") from error
            if kind == "trx":
                results = [x for x in node.iter() if x.tag.endswith("UnitTestResult")]
                if any(x.attrib.get("outcome") != "Passed" for x in results):
                    raise Invalid("TRX contains a failing or unexecuted selected test")
                total += len(results)
            else:
                cases = list(node.iter("testcase"))
                if any(list(case.iter("failure")) or list(case.iter("error")) for case in cases):
                    raise Invalid("JUnit contains a failing selected test")
                total += sum(not list(case.iter("skipped")) for case in cases)
        if not total:
            raise Invalid("No executed tests (empty/all-skipped reports)")
        return total
    output = log.read_text(encoding="utf-8", errors="replace")
    if kind == "go-json":
        cases = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        if any(case.get("Action") == "fail" for case in cases):
            raise Invalid("Go reports a failed package/test")
        count = sum(case.get("Action") == "pass" and bool(case.get("Test")) for case in cases)
    elif kind == "dart-json":
        events = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        if not any(e.get("type") == "done" and e.get("success") is True for e in events):
            raise Invalid("Dart/Flutter did not complete successfully")
        if any(e.get("type") == "error" for e in events):
            raise Invalid("Dart/Flutter reports a test error")
        count = sum(
            e.get("type") == "testDone" and e.get("result") == "success" and not e.get("skipped")
            for e in events
        )
    elif kind == "cargo":
        count = sum(int(n) for n in re.findall(r"test result: ok\. (\d+) passed", output))
    elif kind == "unittest":
        count = sum(int(n) for n in re.findall(r"Ran (\d+) tests?", output))
        if not re.search(r"\bOK\b", output):
            raise Invalid("Native unittest did not report OK")
    elif kind == "native":
        # Project-owned documented regex for a tool lacking JUnit; no default invented success.
        regex = specification.get("positive_pattern")
        if not isinstance(regex, str) or not regex:
            raise Invalid("Native tests need a nonempty positive result expression")
        matches = re.findall(regex, output)
        count = sum(int(n) for n in matches if isinstance(n, str) and n.isdigit())
    else:
        raise Invalid(f"Unsupported test report kind: {kind}")
    if count <= 0:
        raise Invalid("Native tests produced no positive execution result")
    return count


def aggregate(expected: list[str], results: list[dict]) -> dict:
    if not expected or len(set(expected)) != len(expected):
        raise Invalid("A unique nonempty expected result set is required")
    names = [item.get("name") for item in results]
    if len(set(names)) != len(names) or set(names) != set(expected):
        return {"status": "failure", "reason": "Missing, duplicate or unexpected mandatory result"}
    failed = [item["name"] for item in results if item.get("status") != "success"]
    return {"status": "failure" if failed else "success", "failed": failed}
