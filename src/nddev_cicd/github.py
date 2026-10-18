"""Bind native successful PR runs, API-downloaded artifacts and integrated source trees."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .model import Invalid
from .reports import aggregate


def request(path: str) -> urllib.request.Request:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise Invalid("A read-scoped caller token is required for native run provenance")
    return urllib.request.Request(
        "https://api.github.com/" + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nddev-cicd",
        },
    )


def get(path: str):
    with urllib.request.urlopen(request(path), timeout=30) as response:
        return json.load(response)


def eligible(
    repository: str, run_id: int, integrated_revision: str, expected_workflow: str, source: dict | None = None
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise Invalid("Invalid caller repository")
    if not re.fullmatch(r"[0-9a-f]{40}", integrated_revision) or run_id < 1:
        raise Invalid("Exact integrated revision and numeric build run are required")
    run = get(f"repos/{repository}/actions/runs/{run_id}")
    if (
        run["repository"]["full_name"] != repository
        or run["head_repository"]["full_name"] != repository
        or run["event"] != "pull_request"
        or run["status"] != "completed"
        or run["conclusion"] != "success"
        or run["path"] != expected_workflow
    ):
        raise Invalid("Build run is not the expected successful same-repository PR validation")
    pulls = run.get("pull_requests", [])
    if len(pulls) != 1:
        raise Invalid("Exactly one source PR must bind the build candidate")
    pull = get(f"repos/{repository}/pulls/{pulls[0]['number']}")
    if (
        not pull["merged"]
        or pull["merge_commit_sha"] != integrated_revision
        or pull["head"]["sha"] != run["head_sha"]
        or pull["head"]["repo"]["full_name"] != repository
    ):
        raise Invalid("The integrated candidate differs from the trusted completed PR run")
    binding = {
        "repository": repository,
        "head": run["head_sha"],
        "run_id": str(run_id),
        "attempt": str(run["run_attempt"]),
        "event": "pull_request",
    }
    if source is not None:
        if any(source.get(k) != v for k, v in binding.items()):
            raise Invalid("Artifact source differs from the actual PR run/attempt")
        tested = source.get("tested_revision", "")
        if not re.fullmatch(r"[0-9a-f]{40}", tested):
            raise Invalid("Artifact must name an exact tested revision")
        candidate = get(f"repos/{repository}/git/commits/{tested}")
        integrated = get(f"repos/{repository}/git/commits/{integrated_revision}")
        if candidate["tree"]["sha"] != source.get("tested_tree") or candidate["tree"] != integrated["tree"]:
            raise Invalid("Integrated source tree differs from the tested artifact tree")
        parents = {p["sha"] for p in candidate["parents"]}
        if tested != binding["head"] and not {binding["head"], source.get("base")} <= parents:
            raise Invalid("Tested PR merge does not bind the declared head/base")
    return {**binding, "integrated_revision": integrated_revision, "workflow": expected_workflow}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(repository: str, artifact_id: int, destination: Path) -> None:
    # GitHub returns a short-lived object-store URL. Never forward the GitHub token there.
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(request(f"repos/{repository}/actions/artifacts/{artifact_id}/zip"), timeout=30)
    except urllib.error.HTTPError as error:
        if error.code != 302:
            raise
        location = error.headers["Location"]
        if not location.startswith("https://"):
            raise Invalid("Artifact redirect must use HTTPS")
        response = urllib.request.urlopen(location, timeout=60)
    with response, destination.open("wb") as output:
        size = 0
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > 512 * 1024 * 1024:
                raise Invalid("Artifact exceeds the bounded 512MiB delivery bundle limit")
            output.write(chunk)


def bundle(
    repository: str, run_id: int, revision: str, workflow: str, directory: Path
) -> tuple[Path, dict, dict]:
    binding = eligible(repository, run_id, revision, workflow)
    response = get(f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100")
    name = f"nddev-source-{run_id}-{binding['attempt']}-primary"
    matches = [a for a in response["artifacts"] if a["name"] == name and not a["expired"]]
    if len(matches) != 1:
        raise Invalid("No unique nonexpired artifact for the exact successful run attempt")
    directory.mkdir(parents=True, exist_ok=False)
    downloaded = directory / "source.zip"
    download(repository, matches[0]["id"], downloaded)
    required = {"result.json", "artifact.tar.gz", "artifact.tar.gz.json"}
    with zipfile.ZipFile(downloaded) as archive:
        selected = [i for i in archive.infolist() if i.filename in required]
        if len(selected) != 3 or {i.filename for i in selected} != required:
            raise Invalid("Build bundle lacks unique result/archive/manifest members")
        if sum(i.file_size for i in selected) > 512 * 1024 * 1024:
            raise Invalid("Expanded delivery bundle exceeds its limit")
        for member in selected:
            (directory / member.filename).write_bytes(archive.read(member))
    result = json.loads((directory / "result.json").read_text())
    manifest = json.loads((directory / "artifact.tar.gz.json").read_text())
    if (
        result.get("status") != "success"
        or aggregate(result["expected"], result["results"])["status"] != "success"
        or result["identity"] != manifest["source"]
    ):
        raise Invalid("Artifact lacks a complete successful native result")
    eligible(repository, run_id, revision, workflow, manifest["source"])
    for field, environment in (
        ("library_repository", "NDDEV_LIBRARY_REPOSITORY"),
        ("library_ref", "NDDEV_LIBRARY_REF"),
    ):
        if not os.environ.get(environment) or manifest["source"].get(field) != os.environ[environment]:
            raise Invalid("Build and delivery require the same explicitly selected library identity")
    return directory / "artifact.tar.gz", manifest, manifest["source"]
