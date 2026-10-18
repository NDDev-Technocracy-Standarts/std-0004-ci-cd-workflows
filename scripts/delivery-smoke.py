"""Prepare one temporary HTTP target; the pinned public composite performs actual delivery."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from nddev_cicd.github import get

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("operation", choices=["prepare", "serve", "finish"])
parser.add_argument("directory", type=Path)
args = parser.parse_args()
root = args.directory.resolve()
if args.operation == "serve":

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(Handler, directory=str(root / "target/current/dist/target-fixture")),
    )
    (root / "server.json").write_text(
        json.dumps({"pid": os.getpid(), "url": f"http://127.0.0.1:{server.server_port}/"})
    )
    server.serve_forever()
elif args.operation == "prepare":
    if root.exists():
        raise RuntimeError("Never adopt an existing smoke target")
    root.mkdir()
    (root / "target").mkdir()
    repository, revision = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    pulls = get(f"repos/{repository}/commits/{revision}/pulls")
    selected = [pull for pull in pulls if pull.get("merged_at") and pull.get("merge_commit_sha") == revision]
    if len(selected) != 1:
        raise RuntimeError("One exact merged PR must own this integrated source")
    head = selected[0]["head"]["sha"]
    runs = get(
        f"repos/{repository}/actions/workflows/ci.yml/runs?event=pull_request&head_sha={head}&per_page=100"
    )["workflow_runs"]
    runs = [run for run in runs if run["status"] == "completed" and run["conclusion"] == "success"]
    if not runs:
        raise RuntimeError("No completed successful source validation is available")
    run = max(runs, key=lambda value: (value["id"], value["run_attempt"]))
    subprocess.Popen(
        [sys.executable, __file__, "serve", str(root)],
        stdin=subprocess.DEVNULL,
        stdout=(root / "server.log").open("w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for attempt in range(100):
        if (root / "server.json").exists():
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("The temporary target server did not initialize")
    server = json.loads((root / "server.json").read_text())
    config = {
        "module": "static-web",
        "target_directory": str(root / "target"),
        "generation": 1,
        "expected_previous": None,
        "entrypoint": "dist/target-fixture/index.html",
        "health_url": server["url"],
    }
    (root / "target.json").write_text(json.dumps(config))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        print("run_id=" + str(run["id"]), file=output)
        print("target=" + str(root / "target.json"), file=output)
else:
    server_path = root / "server.json"
    if not server_path.exists():
        raise RuntimeError("No owned smoke target was initialized")
    server = json.loads(server_path.read_text())
    try:
        state = json.loads((root / "target/.nddev-deployment.json").read_text())
        assert state["status"] == "success" and not state["pending"]
        with urllib.request.urlopen(server["url"], timeout=5) as response:
            assert state["revision"] in response.read().decode()
        print(
            json.dumps(
                {
                    "status": "success",
                    "artifact": state["artifact"],
                    "tested_revision": state["revision"],
                    "integrated_revision": os.environ["GITHUB_SHA"],
                    "target": "temporary loopback fixture",
                }
            )
        )
    finally:
        os.kill(server["pid"], 15)
