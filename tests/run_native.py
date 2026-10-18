"""Run real native fixture profiles in isolated Git checkouts, including rejected source errors."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

from nddev_cicd.ci import execute
from nddev_cicd.config import load
from nddev_cicd.package_check import check as consumer_check

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
    "ruby": "lib/native_checksum.rb",
    "architecture": "src/native_graph/domain.py",
    "infrastructure": "main.tf",
    "container": "Dockerfile",
    "php": "src/Checksum.php",
    "security": "app.py",
    "r": "R/checksum.R",
    "android": "app/src/main/kotlin/com/nddev/ci/fixture/MainActivity.kt",
}


def exercise(name: str, output: Path) -> dict:
    fixture = Path(__file__).with_name("native") / name
    if name not in SOURCES or not fixture.is_dir():
        raise ValueError(f"No integrated native fixture for {name}")
    with tempfile.TemporaryDirectory(prefix=f"nddev-native-{name}-") as directory, ExitStack() as cleanup:
        root = Path(directory) / "caller"
        standard_ignores = shutil.ignore_patterns(
            ".venv",
            "target",
            "build",
            "dist",
            "__pycache__",
            ".pytest_cache",
            ".nddev-reports",
            "vendor",
            ".terraform",
            ".gradle",
        )

        def ignored(path, names):
            omitted = standard_ignores(path, names)
            if name == "r" and Path(path).name == "renv":
                omitted.update({"library", "staging"} & set(names))
            return omitted

        shutil.copytree(
            fixture,
            root,
            ignore=ignored,
        )
        if name == "container":
            cleanup.callback(
                subprocess.run, [sys.executable, str(root / "native.py"), "cleanup"], cwd=root, check=False
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
        if name == "python":
            try:
                consumer_check(root, {"commands": [["python", "--version"]]})
            except subprocess.CalledProcessError:
                pass
            else:
                raise RuntimeError("A system executable cannot stand in for the built distribution's CLI")
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
        if name == "security":
            source.write_text(
                source.read_text().replace(
                    "yaml.safe_load(payload)", "yaml.load(payload, Loader=yaml.Loader)"
                )
            )
        elif name == "architecture":
            # A valid Python import closes a real adapter/domain cycle and violates the declared boundary.
            source.write_text(source.read_text() + "\nfrom . import adapter\n")
        elif name == "advanced":
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
        if name == "architecture":
            source.write_text(source.read_text().replace("\nfrom . import adapter\n", ""))
            settings = load(root)
            settings["architecture"]["scopes"] = ["src/unmatched_module"]
            unmatched = execute(root, settings, output / "unmatched-scope")
            if unmatched["status"] != "failure" or "architecture.scope" not in unmatched["failed"]:
                raise RuntimeError("An unmatched architectural scope cannot be vacuous success")
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
