"""Run real native fixture profiles in isolated Git checkouts, including rejected source errors."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from nddev_cicd.ci import execute
from nddev_cicd.config import load

SOURCES = {
    "python": "src/ciwf_fixture/__init__.py",
    "rust": "src/lib.rs",
    "go": "checksum.go",
    "cpp": "src/main.cpp",
}


def exercise(name: str, output: Path) -> dict:
    fixture = Path(__file__).with_name("native") / name
    if name not in SOURCES or not fixture.is_dir():
        raise ValueError(f"No integrated native fixture for {name}")
    with tempfile.TemporaryDirectory(prefix=f"nddev-native-{name}-") as directory:
        root = Path(directory) / "caller"
        shutil.copytree(
            fixture,
            root,
            ignore=shutil.ignore_patterns(
                ".venv", "target", "build", "dist", "__pycache__", ".pytest_cache", ".nddev-reports"
            ),
        )
        for args in (
            ["init", "-b", "main"],
            ["config", "user.name", "Fixture"],
            ["config", "user.email", "fixture@example.invalid"],
            ["add", "."],
            ["commit", "-qm", "native fixture"],
        ):
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
        positive = execute(root, load(root), output / "positive")
        if positive["status"] != "success":
            raise RuntimeError(f"Native {name} fixture failed: {positive.get('failed')}; logs: {output}")
        # A genuine source syntax error must reach the real compiler/test path and remain a failed aggregate.
        source = root / SOURCES[name]
        source.write_text(source.read_text() + "\nNDDEV deliberately invalid native source !\n")
        negative = execute(root, load(root), output / "negative")
        if negative["status"] != "failure" or not negative.get("failed"):
            raise RuntimeError(f"Native {name} accepted deliberately invalid source")
        return {
            "profile": name,
            "positive": "success",
            "negative": "rejected",
            "result_directory": str(output),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=sorted(SOURCES))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(exercise(args.profile, args.output.resolve())))
