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
    "node": "checksum.js",
    "dotnet": "src/Checksum/Class1.cs",
    "sql": "migrations/002.sql",
    "advanced": "checksum.py",
    "shell": "checksum.sh",
    "qt": "src/fixture_identity.cpp",
    "flutter": "lib/main.dart",
    "swift": "Sources/CiwfFixture/Checksum.swift",
    "jvm": "src/main/java/example/Checksum.java",
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
        if name == "go":
            source = root / SOURCES[name]
            original = source.read_text()
            source.write_text(original.replace("func Checksum(", "func Checksum( "))
            formatting = execute(root, load(root), output / "format-negative")
            if (
                "go.format" not in formatting.get("failed", [])
                or next(i for i in formatting["results"] if i["name"] == "go.test")["status"] != "success"
            ):
                raise RuntimeError("Native formatting drift must fail independently of passing Go tests")
            source.write_text(original)
        # A genuine source syntax error must reach the real compiler/test path and remain a failed aggregate.
        source = root / SOURCES[name]
        if name == "advanced":
            source.write_text(source.read_text().replace("sum(payload) % 256", "(sum(payload) + 1) % 256"))
        else:
            source.write_text(source.read_text() + "\nNDDEV deliberately invalid native source !\n")
        negative = execute(root, load(root), output / "negative")
        if negative["status"] != "failure" or not negative.get("failed"):
            raise RuntimeError(f"Native {name} accepted deliberately invalid source")
        if (
            name == "cpp"
            and next(i for i in negative["results"] if i["name"] == "c-cpp.test")["status"] != "unavailable"
        ):
            raise RuntimeError("A failed native build cannot validate an old test binary")
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
