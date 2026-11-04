"""Free native security commands; callers own source scopes and license policy."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .impact import matches
from .model import Invalid, contained, git, git_environment
from .process import run

CRITICAL_SCORE = 9.0
# osv-scanner exits 1 when it found vulnerabilities and 128 when the source has no packages.
OSV_COMPLETED = {0, 1, 128}


def semgrep_sources(root: Path, settings: dict) -> list[str]:
    scopes = settings.get("paths")
    if not isinstance(scopes, list) or not scopes:
        raise Invalid("Semgrep requires explicit tracked source scopes")
    tracked = [name for name in git(root, "ls-files", "-z").split("\0") if name]
    selected = set()
    for scope in scopes:
        if not isinstance(scope, str) or not scope or Path(scope).is_absolute() or ".." in Path(scope).parts:
            raise Invalid("Semgrep source scopes must stay in the caller checkout")
        found = [name for name in tracked if matches(name, scope)]
        if not found:
            raise Invalid("Semgrep source scope has no tracked files: " + scope)
        for name in found:
            if (root / name).is_symlink() or not contained(root, name, exists=True).is_file():
                raise Invalid("Semgrep scans contained regular source files")
        selected.update(found)
    return sorted(selected)


def verify_semgrep(root: Path, settings: dict, log: Path) -> int:
    report = json.loads(log.read_text())
    if not report.get("version") or report.get("errors"):
        raise Invalid("Semgrep did not establish a complete native analysis")
    scanned = report.get("paths", {}).get("scanned", [])
    actual = set()
    for name in scanned:
        path = Path(name)
        path = path if path.is_absolute() else root / path
        if not path.resolve().is_relative_to(root.resolve()):
            raise Invalid("Semgrep reported an unexpected source target")
        actual.add(path.resolve().relative_to(root.resolve()).as_posix())
    if actual != set(semgrep_sources(root, settings)):
        raise Invalid("Semgrep did not analyze every explicitly selected source file")
    return len(actual)


def semgrep_findings(log: Path) -> int:
    """Count reported Semgrep findings; they inform and never stop a merge."""
    return len(json.loads(log.read_text()).get("results") or [])


def native_command(helper: str, root: Path, contract: dict) -> list[str]:
    settings = contract.get("security", {})
    if helper == "security-licenses":
        licenses = settings.get("licenses")
        if (
            not isinstance(licenses, list)
            or not licenses
            or any(
                not isinstance(x, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", x) for x in licenses
            )
        ):
            raise Invalid("Default license checking requires an explicit SPDX security.licenses allowlist")
        return ["osv-scanner", "scan", "source", "--recursive", "--licenses=" + ",".join(licenses), "."]
    if settings.get("engine") == "semgrep":
        rules = settings.get("rules")
        if not isinstance(rules, list) or not 1 <= len(rules) <= 32:
            raise Invalid("Semgrep CE requires an explicit bounded local rule selection")
        command = [
            "semgrep",
            "scan",
            "--oss-only",
            "--metrics=off",
            "--disable-version-check",
            "--strict",
            "--json",
            "--no-git-ignore",
        ]
        for rule in rules:
            if not isinstance(rule, str):
                raise Invalid("Semgrep rules must be tracked local files")
            path = contained(root, rule, exists=True)
            if not path.is_file() or (root / rule).is_symlink() or not git(root, "ls-files", "--", rule):
                raise Invalid("Semgrep rules must be contained tracked regular files")
            command.extend(["--config", str(path)])
        return [*command, "--", *semgrep_sources(root, settings)]
    scopes = settings.get("python")
    if (
        not isinstance(scopes, list)
        or not scopes
        or any(
            not isinstance(x, str) or not x or Path(x).is_absolute() or ".." in Path(x).parts for x in scopes
        )
    ):
        raise Invalid("Default Python SAST requires explicit security.python tracked source globs")
    tracked = [x for x in git(root, "ls-files", "-z").split("\0") if x.endswith(".py")]
    selected = set()
    for scope in scopes:
        found = [x for x in tracked if matches(x, scope)]
        if not found:
            raise Invalid("Python SAST scope has no tracked source: " + scope)
        for relative in found:
            if (root / relative).is_symlink() or not contained(root, relative, exists=True).is_file():
                raise Invalid("Python SAST requires contained regular source files")
        selected.update(found)
    # Findings are reported, not blocking: a merge stops only for the three security cases.
    return ["bandit", "--quiet", "--exit-zero", "--", *sorted(selected)]


def change_range(root: Path, base: str | None, head: str) -> str | None:
    """Return the commit range of the change, or None when only the full history can be scanned."""
    if not base or not re.fullmatch(r"[0-9a-f]{40}", base):
        return None
    try:
        count = int(git(root, "rev-list", "--count", f"{base}..{head}"))
    except (Invalid, ValueError):
        return None
    return f"{base}..{head}" if count else None


def _critical(vulnerability: dict, max_severity: str | None) -> bool:
    try:
        if max_severity and float(max_severity) >= CRITICAL_SCORE:
            return True
    except ValueError:
        pass
    level = str(vulnerability.get("database_specific", {}).get("severity", ""))
    return level.upper() == "CRITICAL"


def _fixed(vulnerability: dict, name: str) -> bool:
    for affected in vulnerability.get("affected", []):
        package = affected.get("package", {})
        if package.get("name") not in (None, name):
            continue
        for selected in affected.get("ranges", []):
            if any(event.get("fixed") for event in selected.get("events", [])):
                return True
    return False


def osv_findings(report: dict) -> dict[tuple[str, str, str], dict]:
    """Index osv-scanner JSON findings by ecosystem, package and vulnerability."""
    findings = {}
    for result in report.get("results") or []:
        for package in result.get("packages") or []:
            info = package.get("package", {})
            severity = {}
            for group in package.get("groups") or []:
                for identifier in [*group.get("ids", []), *group.get("aliases", [])]:
                    severity[identifier] = group.get("max_severity")
            for vulnerability in package.get("vulnerabilities") or []:
                identifier = vulnerability.get("id", "")
                key = (str(info.get("ecosystem", "")), str(info.get("name", "")), identifier)
                findings[key] = {
                    "id": identifier,
                    "package": info.get("name", ""),
                    "version": info.get("version", ""),
                    "ecosystem": info.get("ecosystem", ""),
                    "source": result.get("source", {}).get("path", ""),
                    "critical": _critical(vulnerability, severity.get(identifier)),
                    "fixed": _fixed(vulnerability, str(info.get("name", ""))),
                }
    return findings


def _scan(command: list[str], root: Path, report: Path, log: Path) -> dict:
    result = run([*command, "--format", "json", "--output", str(report)], root, log, timeout=900)
    if result["exit_code"] not in OSV_COMPLETED:
        return {**result, "status": "failure", "detail": "osv-scanner could not complete the scan"}
    try:
        data = json.loads(report.read_text()) if report.is_file() and report.stat().st_size else {}
    except ValueError:
        return {**result, "status": "failure", "detail": "osv-scanner wrote no readable JSON report"}
    return {**result, "status": "success", "findings": osv_findings(data)}


def dependencies(root: Path, command: list[str], base: str | None, head: str, output: Path) -> dict:
    """Report every dependency finding; stop only a pull request that brings in a critical one with a fix."""
    output.mkdir(parents=True, exist_ok=True)
    current = _scan(command, root, output / "osv-head.json", output / "dependencies.log")
    if current["status"] != "success":
        return {key: value for key, value in current.items() if key != "findings"}
    findings = current.pop("findings")
    pull_request = os.environ.get("GITHUB_EVENT_NAME") in {"pull_request", "pull_request_target"}
    previous: dict | None = None
    if pull_request and change_range(root, base, head):
        with tempfile.TemporaryDirectory(prefix="nddev-osv-base-") as temporary:
            tree = Path(temporary) / "base"
            added = subprocess.run(
                ["git", "-C", str(root), "worktree", "add", "--detach", "--quiet", str(tree), str(base)],
                check=False,
                capture_output=True,
                text=True,
                env=git_environment(),
            )
            if added.returncode == 0:
                try:
                    scanned = _scan(command, tree, output / "osv-base.json", output / "dependencies-base.log")
                    if scanned["status"] == "success":
                        previous = scanned["findings"]
                finally:
                    subprocess.run(
                        ["git", "-C", str(root), "worktree", "remove", "--force", str(tree)],
                        check=False,
                        capture_output=True,
                        env=git_environment(),
                    )
    introduced = [item for key, item in findings.items() if previous is not None and key not in previous]
    stopping = [item for item in introduced if item["critical"] and item["fixed"]]
    summary = {
        "findings": len(findings),
        "introduced": len(introduced) if previous is not None else None,
        "stopping": [f"{x['package']} {x['version']}: {x['id']}" for x in stopping],
    }
    with open(current["log"], "a") as log:
        log.write("Dependency findings: " + json.dumps(summary, sort_keys=True) + "\n")
    if stopping:
        return {
            **current,
            **summary,
            "status": "failure",
            "detail": "The change brings in a critical vulnerability that has a fix: "
            + ", ".join(summary["stopping"]),
        }
    detail = f"{len(findings)} dependency findings reported"
    if pull_request and previous is None:
        detail += "; the base could not be scanned, so nothing stops the merge"
    return {**current, **summary, "status": "success", "detail": detail}


TRUFFLEHOG = ["trufflehog", "git", "--json", "--no-update", "--results=verified,unknown"]
DAILY_TITLE = "Daily security report"


def _secret_findings(log: Path) -> list[dict]:
    """Read TruffleHog JSON lines; the secret value itself is never kept."""
    found = []
    for line in log.read_text().splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict) or "DetectorName" not in record:
            continue
        place = record.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
        found.append(
            {
                "detector": str(record.get("DetectorName", "")),
                "verified": bool(record.get("Verified")),
                "file": str(place.get("file", "")),
                "commit": str(place.get("commit", ""))[:12],
                "line": place.get("line"),
            }
        )
    return found


def _table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def daily(root: Path, output: Path, day: str) -> dict:
    """Scan the whole history for live secrets and report every dependency finding.

    A finding never fails the run. A scanner that cannot run does.
    """
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    secrets_log = output / "trufflehog.jsonl"
    scanned = run(
        [*TRUFFLEHOG[:2], "file://" + str(root.resolve()), *TRUFFLEHOG[2:]],
        root,
        secrets_log,
        timeout=3600,
        stderr_log=output / "trufflehog.stderr.log",
    )
    secrets = _secret_findings(secrets_log) if scanned["exit_code"] == 0 else []
    if scanned["exit_code"] != 0:
        failures.append("TruffleHog could not complete the history scan")
    dependency = _scan(
        ["osv-scanner", "scan", "source", "--recursive", "."], root, output / "osv.json", output / "osv.log"
    )
    findings = list(dependency.get("findings", {}).values()) if dependency["status"] == "success" else []
    if dependency["status"] != "success":
        failures.append(dependency["detail"])
    lines = [f"Findings on {day}. Fix each one the same day, starting with verified secrets and critical"]
    lines += ["vulnerabilities that have a fix.", ""]
    lines += [f"## Live secrets in the whole history: {len(secrets)}", ""]
    if secrets:
        lines += _table(
            ["Detector", "Verified", "File", "Commit", "Line"],
            [
                [x["detector"], "yes" if x["verified"] else "unknown", x["file"], x["commit"], x["line"]]
                for x in secrets
            ],
        )
        lines += [
            "",
            "Revoke a leaked secret first, then issue a new one and rotate what it could reach.",
            "",
        ]
    lines += [f"## Dependency vulnerabilities: {len(findings)}", ""]
    if findings:
        ordered = sorted(findings, key=lambda x: (not x["critical"], not x["fixed"], x["package"], x["id"]))
        lines += _table(
            ["Package", "Version", "Vulnerability", "Critical", "Fix exists", "Source"],
            [
                [
                    x["package"],
                    x["version"],
                    x["id"],
                    "yes" if x["critical"] else "no",
                    "yes" if x["fixed"] else "no",
                    x["source"],
                ]
                for x in ordered
            ],
        )
    if failures:
        lines += ["", "## Scanners that could not run", "", *["- " + x for x in failures]]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    summary = {
        "status": "failure" if failures else "success",
        "secrets": len(secrets),
        "dependencies": len(findings),
        "findings": len(secrets) + len(findings),
        "failures": failures,
        "report": str(output / "report.md"),
    }
    atomic = output / "summary.json"
    atomic.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary
