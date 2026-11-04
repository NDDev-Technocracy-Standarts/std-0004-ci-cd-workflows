"""Native scanner scope and result validation cannot substitute empty work for feedback."""

import json
import os

import pytest

from nddev_cicd import security
from nddev_cicd.model import Invalid, git


def test_semgrep_requires_local_tracked_rules_and_real_source(repository):
    root = repository({"source.js": "const result = 1;\n", "rules.yml": "rules: []\n"})
    settings = {"engine": "semgrep", "paths": ["source.js"], "rules": ["rules.yml"]}
    with pytest.raises(Invalid):
        security.native_command(
            "security-sast", root, {"security": {**settings, "rules": ["https://example.invalid/rules.yml"]}}
        )
    with pytest.raises(Invalid):
        security.native_command("security-sast", root, {"security": {**settings, "paths": ["missing/*.js"]}})
    (root / "untracked.yml").write_text("rules: []\n")
    with pytest.raises(Invalid, match="tracked"):
        security.native_command("security-sast", root, {"security": {**settings, "rules": ["untracked.yml"]}})


@pytest.mark.parametrize(
    "scanned,errors,results",
    [([], [], []), (["other.js"], [], []), (["source.js"], [{}], [])],
)
def test_native_semgrep_cannot_omit_source_or_hide_errors(repository, tmp_path, scanned, errors, results):
    root = repository({"source.js": "const result = 1;\n"})
    log = tmp_path / "scanner.json"
    log.write_text(
        json.dumps(
            {"version": "fixture", "paths": {"scanned": scanned}, "errors": errors, "results": results}
        )
    )
    with pytest.raises(Invalid):
        security.verify_semgrep(root, {"paths": ["source.js"]}, log)


def test_semgrep_findings_are_reported_not_blocking(repository, tmp_path):
    root = repository({"source.js": "const result = 1;\n"})
    log = tmp_path / "scanner.json"
    log.write_text(
        json.dumps(
            {"version": "fixture", "paths": {"scanned": ["source.js"]}, "errors": [], "results": [{}, {}]}
        )
    )
    assert security.verify_semgrep(root, {"paths": ["source.js"]}, log) == 1
    assert security.semgrep_findings(log) == 2


def osv_report(identifier="GHSA-0001", severity="9.8", fixed=True, name="left-pad", version="1.0.0"):
    events = [{"introduced": "0"}, {"fixed": "1.0.1"}] if fixed else [{"introduced": "0"}]
    return {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"name": name, "version": version, "ecosystem": "npm"},
                        "vulnerabilities": [
                            {
                                "id": identifier,
                                "affected": [{"package": {"name": name}, "ranges": [{"events": events}]}],
                            }
                        ],
                        "groups": [{"ids": [identifier], "aliases": [], "max_severity": severity}],
                    }
                ],
            }
        ]
    }


def test_osv_findings_know_critical_and_fixed():
    found = security.osv_findings(osv_report())
    assert found[("npm", "left-pad", "GHSA-0001")] | {} == {
        "id": "GHSA-0001",
        "package": "left-pad",
        "version": "1.0.0",
        "ecosystem": "npm",
        "source": "package-lock.json",
        "critical": True,
        "fixed": True,
    }
    assert not security.osv_findings(osv_report(severity="7.5"))[("npm", "left-pad", "GHSA-0001")]["critical"]
    assert not security.osv_findings(osv_report(fixed=False))[("npm", "left-pad", "GHSA-0001")]["fixed"]
    labelled = osv_report(severity="")
    labelled["results"][0]["packages"][0]["vulnerabilities"][0]["database_specific"] = {
        "severity": "CRITICAL"
    }
    assert security.osv_findings(labelled)[("npm", "left-pad", "GHSA-0001")]["critical"]
    assert security.osv_findings({"results": None}) == {}


FAKE_OSV = """#!/bin/sh
# Writes the osv.json of the scanned checkout to --output and exits like osv-scanner.
out=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--output" ]; then out="$2"; shift; fi
  shift
done
cp osv.json "$out"
grep -q '"vulnerabilities"' osv.json && exit 1
exit 0
"""


def pull_request_change(repository, tmp_path, monkeypatch, base_report, head_report):
    root = repository({"osv.json": json.dumps(base_report)})
    base = git(root, "rev-parse", "HEAD")
    (root / "osv.json").write_text(json.dumps(head_report))
    (root / "change.txt").write_text("the change\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "change")
    head = git(root, "rev-parse", "HEAD")
    tools = tmp_path / "tools"
    tools.mkdir()
    scanner = tools / "osv-scanner"
    scanner.write_text(FAKE_OSV)
    scanner.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    command = ["osv-scanner", "scan", "source", "--recursive", "."]
    return root, base, head, command


def test_only_an_introduced_critical_vulnerability_with_a_fix_stops_a_pull_request(
    repository, tmp_path, monkeypatch
):
    clean = {"results": []}
    root, base, head, command = pull_request_change(repository, tmp_path, monkeypatch, clean, osv_report())
    result = security.dependencies(root, command, base, head, tmp_path / "out")
    assert result["status"] == "failure"
    assert result["stopping"] == ["left-pad 1.0.0: GHSA-0001"]
    assert not list((tmp_path / "out").glob("base*"))


@pytest.mark.parametrize(
    "base_report,head_report",
    [
        (osv_report(), osv_report(version="1.0.0")),
        ({"results": []}, osv_report(severity="7.5")),
        ({"results": []}, osv_report(fixed=False)),
    ],
    ids=["already-present", "not-critical", "no-fix"],
)
def test_other_dependency_findings_are_reported(repository, tmp_path, monkeypatch, base_report, head_report):
    root, base, head, command = pull_request_change(
        repository, tmp_path, monkeypatch, base_report, head_report
    )
    result = security.dependencies(root, command, base, head, tmp_path / "out")
    assert result["status"] == "success"
    assert result["findings"] == 1
    assert result["stopping"] == []


def test_dependency_findings_never_stop_a_push(repository, tmp_path, monkeypatch):
    root, base, head, command = pull_request_change(
        repository, tmp_path, monkeypatch, {"results": []}, osv_report()
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    result = security.dependencies(root, command, base, head, tmp_path / "out")
    assert result["status"] == "success"
    assert result["introduced"] is None


def test_scanner_failure_is_a_failure(repository, tmp_path, monkeypatch):
    root, base, head, command = pull_request_change(
        repository, tmp_path, monkeypatch, {"results": []}, {"results": []}
    )
    (tmp_path / "tools" / "osv-scanner").write_text("#!/bin/sh\nexit 127\n")
    result = security.dependencies(root, command, base, head, tmp_path / "out")
    assert result["status"] == "failure"


def test_change_range_covers_only_the_commits_of_the_change(repository):
    root = repository({"a.txt": "a"})
    base = git(root, "rev-parse", "HEAD")
    assert security.change_range(root, base, base) is None
    assert security.change_range(root, None, base) is None
    assert security.change_range(root, "0" * 40, base) is None
    (root / "a.txt").write_text("b")
    git(root, "commit", "-qam", "change")
    head = git(root, "rev-parse", "HEAD")
    assert security.change_range(root, base, head) == f"{base}..{head}"


FAKE_TRUFFLEHOG = """#!/bin/sh
cat <<'JSON'
{"level":"info-0","msg":"running source"}
{"SourceMetadata":{"Data":{"Git":{"commit":"8c0dd9995b4cbeeaf49b7215974f10b2d64beb6c","file":"leak.txt","line":1}}},"DetectorName":"AWS","Verified":true,"Raw":"AKIA-secret-value"}
JSON
"""


def test_daily_report_lists_findings_without_secret_values(repository, tmp_path, monkeypatch):
    root = repository({"osv.json": json.dumps(osv_report())})
    tools = tmp_path / "tools"
    tools.mkdir()
    for name, body in (("trufflehog", FAKE_TRUFFLEHOG), ("osv-scanner", FAKE_OSV)):
        (tools / name).write_text(body)
        (tools / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    summary = security.daily(root, tmp_path / "daily", "2026-11-04")
    assert summary["status"] == "success"
    assert (summary["secrets"], summary["dependencies"], summary["findings"]) == (1, 1, 2)
    report = (tmp_path / "daily" / "report.md").read_text()
    assert "| AWS | yes | leak.txt | 8c0dd9995b4c | 1 |" in report
    assert "| left-pad | 1.0.0 | GHSA-0001 | yes | yes | package-lock.json |" in report
    assert "AKIA-secret-value" not in report
    assert "secret-value" not in (tmp_path / "daily" / "summary.json").read_text()


def test_daily_fails_only_when_a_scanner_cannot_run(repository, tmp_path, monkeypatch):
    root = repository({"osv.json": json.dumps({"results": []})})
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "trufflehog").write_text("#!/bin/sh\nexit 2\n")
    (tools / "osv-scanner").write_text(FAKE_OSV)
    for name in ("trufflehog", "osv-scanner"):
        (tools / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    summary = security.daily(root, tmp_path / "daily", "2026-11-04")
    assert summary["status"] == "failure"
    assert summary["failures"] == ["TruffleHog could not complete the history scan"]
    assert "Scanners that could not run" in (tmp_path / "daily" / "report.md").read_text()
