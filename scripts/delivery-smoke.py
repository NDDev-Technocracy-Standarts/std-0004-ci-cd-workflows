"""Prepare a separate owned SSH server; deliver the exact successful PR artifact remotely."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from nddev_cicd.github import get

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
import ssh_fixture

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("operation", choices=["prepare", "finish"])
parser.add_argument("directory", type=Path)
args = parser.parse_args()
root = args.directory.resolve()
if args.operation == "prepare":
    root.mkdir(exist_ok=False)
    repository, revision = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    selected = [
        p
        for p in get(f"repos/{repository}/commits/{revision}/pulls")
        if p.get("merged_at") and p.get("merge_commit_sha") == revision
    ]
    if len(selected) != 1:
        raise RuntimeError("One exact merged PR must own this integrated source")
    head = selected[0]["head"]["sha"]
    runs = get(
        f"repos/{repository}/actions/workflows/ci.yml/runs?event=pull_request&head_sha={head}&per_page=100"
    )["workflow_runs"]
    runs = [r for r in runs if r["status"] == "completed" and r["conclusion"] == "success"]
    if not runs:
        raise RuntimeError("No completed successful source validation is available")
    run = max(runs, key=lambda r: (r["id"], r["run_attempt"]))
    fixture = ssh_fixture.start(root / "server")
    config = {
        "module": "static-web",
        "target_directory": fixture["target"],
        "generation": 1,
        "expected_previous": None,
        "entrypoint": "dist/target-fixture/index.html",
        "health_url": "http://127.0.0.1:8080/current/dist/target-fixture/",
    }
    (root / "target.json").write_text(json.dumps(config))
    (root / "transport.json").write_text(json.dumps(fixture["transport"]))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        print("run_id=" + str(run["id"]), file=output)
        print("target=" + str(root / "target.json"), file=output)
        print("transport=" + str(root / "transport.json"), file=output)
else:
    fixture = json.loads((root / "server/fixture.json").read_text())
    try:
        with urllib.request.urlopen(fixture["http_url"] + "/.nddev-deployment.json", timeout=5) as response:
            state = json.load(response)
        if state.get("status") != "success" or state.get("pending"):
            raise RuntimeError("The separate SSH target did not accept this artifact")
        with urllib.request.urlopen(
            fixture["http_url"] + "/current/dist/target-fixture/", timeout=5
        ) as response:
            if state["revision"] not in response.read().decode():
                raise RuntimeError("The remote server does not serve the tested revision")
        print(
            json.dumps(
                {
                    "status": "success",
                    "artifact": state["artifact"],
                    "tested_revision": state["revision"],
                    "integrated_revision": os.environ["GITHUB_SHA"],
                    "target": "separate isolated SSH server/filesystem; no production deployment",
                }
            )
        )
    finally:
        ssh_fixture.stop(root / "server")
