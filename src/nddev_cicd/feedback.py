"""Bounded metadata-only failure feedback; candidate code and logs are never executed."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from . import github
from .model import Invalid

CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}


def write(path: str, payload: dict) -> dict:
    req = github.request(path)
    req.method = "POST"
    req.data = json.dumps(payload).encode()
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def pages(path: str, limit: int = 5) -> list[dict]:
    records = []
    for page in range(1, limit + 1):
        batch = github.get(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise Invalid("Unexpected paginated feedback response")
        records.extend(batch)
        if len(batch) < 100:
            return records
    raise Invalid("Feedback pagination budget exhausted; reconcile explicitly before retrying")


def publish(
    repository: str,
    workflows: list[str],
    creators: list[str],
    *,
    run_id: int | None = None,
    conclusions: list[str] | None = None,
    task_issue: int | None = None,
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise Invalid("Select an exact caller repository")
    if (
        not workflows
        or len(workflows) > 10
        or any(not re.fullmatch(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", p) for p in workflows)
    ):
        raise Invalid("Select bounded exact workflow paths")
    if (
        not creators
        or len(creators) > 32
        or any(not re.fullmatch(r"[A-Za-z0-9_-]+(?:\[bot\])?", p) for p in creators)
    ):
        raise Invalid("Feedback requires an explicit creator allowlist")
    conclusions = conclusions or ["failure", "timed_out", "action_required", "startup_failure"]
    if not conclusions or set(conclusions) - CONCLUSIONS:
        raise Invalid("Feedback only publishes selected non-success conclusions")
    if run_id is not None and (type(run_id) is not int or run_id < 1):
        raise Invalid("Feedback run ID must be positive")
    if task_issue is not None and (type(task_issue) is not int or task_issue < 1):
        raise Invalid("Feedback task Issue must be positive")
    prefix = f"repos/{repository}"
    if run_id is not None:
        candidates = [github.get(f"{prefix}/actions/runs/{run_id}")]
    else:
        candidates = []
        for workflow in workflows:
            key = urllib.parse.quote(workflow.rsplit("/", 1)[1], safe="")
            candidates.extend(
                github.get(f"{prefix}/actions/workflows/{key}/runs?status=completed&per_page=20")[
                    "workflow_runs"
                ]
            )
    actions = []
    for run in candidates:
        if (
            run.get("repository", {}).get("full_name") != repository
            or run.get("path") not in workflows
            or run.get("actor", {}).get("login") not in creators
            or run.get("status") != "completed"
            or run.get("conclusion") not in conclusions
        ):
            continue
        number, attempt = run.get("id"), run.get("run_attempt")
        if type(number) is not int or number < 1 or type(attempt) is not int or attempt < 1:
            raise Invalid("Native run/attempt identity is absent")
        marker = f"<!-- nddev-ci-feedback:{number}:{attempt} -->"
        # Since creation bounds recent Issue reads while retaining closed markers for old reruns.
        created = run.get("created_at", "")
        if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", created):
            raise Invalid("Native run creation time is absent")
        body = (
            f"{marker}\nNative workflow `{run['path']}` concluded `{run['conclusion']}`.\n\n"
            f"[Inspect the exact run attempt](https://github.com/{repository}/actions/runs/{number}/attempts/{attempt}).\n\n"
            "The owning agent must inspect the native diagnostics and resolve or record the failure. "
            "This publisher reads metadata only and does not execute candidate code or download artifacts.\n"
        )
        trusted_publishers = {"github-actions[bot]", *creators}
        if task_issue:
            issue = github.get(f"{prefix}/issues/{task_issue}")
            existing = [issue, *pages(f"{prefix}/issues/{task_issue}/comments")]
            if any(
                marker in (i.get("body") or "") and i.get("user", {}).get("login") in trusted_publishers
                for i in existing
            ):
                actions.append({"run": number, "attempt": attempt, "action": "existing", "issue": task_issue})
                continue
            published = write(f"{prefix}/issues/{task_issue}/comments", {"body": body})
        else:
            issues = pages(
                f"{prefix}/issues?state=all&sort=created&direction=desc&since={urllib.parse.quote(created)}"
            )
            found = next(
                (
                    i
                    for i in issues
                    if marker in (i.get("body") or "")
                    and i.get("user", {}).get("login") in trusted_publishers
                ),
                None,
            )
            if found:
                actions.append(
                    {"run": number, "attempt": attempt, "action": "existing", "issue": found["number"]}
                )
                continue
            published = write(
                f"{prefix}/issues",
                {
                    "title": f"Resolve {run['path'].rsplit('/', 1)[1]} run {number} attempt {attempt}",
                    "body": body,
                },
            )
        actions.append(
            {"run": number, "attempt": attempt, "action": "published", "url": published["html_url"]}
        )
    return {"status": "success", "results": actions}
