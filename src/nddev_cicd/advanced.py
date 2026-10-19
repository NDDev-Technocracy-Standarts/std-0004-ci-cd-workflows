"""Bounded native fuzzing, mutation and benchmark gates; native outputs establish actual work."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path

from .model import Invalid, atomic_json, contained, digest, source_identity
from .process import run


def fuzz(
    root: Path,
    output: Path,
    target: str,
    *,
    engine="rust",
    corpus="fuzz/corpus",
    runs=1000,
    seconds=30,
    toolchain="nightly-2026-10-19",
    fuzz_directory="fuzz",
) -> dict:
    if (
        type(runs) is not int
        or not 1 <= runs <= 1000000
        or type(seconds) is not int
        or not 1 <= seconds <= 900
    ):
        raise Invalid("Fuzzing needs explicit finite input/time budgets")
    output.mkdir(parents=True, exist_ok=False)
    failures = output / "failing-inputs"
    failures.mkdir()
    seeds = contained(root, corpus, exists=True)
    if not seeds.is_dir():
        raise Invalid("Select an existing native corpus directory")
    if any(p.is_symlink() for p in seeds.rglob("*")):
        raise Invalid("Fuzz seed corpus must not follow foreign symlinks")
    corpus_inputs = {p.relative_to(seeds).as_posix(): digest(p) for p in seeds.rglob("*") if p.is_file()}
    owned_corpus = output / "corpus"
    shutil.copytree(seeds, owned_corpus)
    arguments = [
        "-runs=" + str(runs),
        "-max_total_time=" + str(seconds),
        "-artifact_prefix=" + str(failures) + "/",
    ]
    environment = {}
    lock, before = None, None
    if engine == "rust":
        if not re.fullmatch(r"[A-Za-z0-9_-]+", target) or not re.fullmatch(
            r"nightly-\d{4}-\d{2}-\d{2}", toolchain
        ):
            raise Invalid("Select a native target and a pinned installed nightly compiler")
        compiler = Path(
            subprocess.check_output(["rustup", "which", "--toolchain", toolchain, "rustc"], text=True).strip()
        )
        cargo = compiler.with_name("cargo")
        version = subprocess.check_output([str(compiler), "-vV"], text=True)
        if "nightly" not in version:
            raise Invalid("The compiler actually selected for fuzzing is not nightly")
        triple = next(line.split(": ", 1)[1] for line in version.splitlines() if line.startswith("host: "))
        directory = contained(root, fuzz_directory, exists=True)
        lock = directory / "Cargo.lock"
        if not lock.is_file():
            raise Invalid("Native Rust fuzzing requires its committed dependency lock")
        before = digest(lock)
        environment = {
            "RUSTC": str(compiler),
            "RUSTDOC": str(compiler.with_name("rustdoc")),
            "PATH": str(compiler.parent) + os.pathsep + os.environ.get("PATH", ""),
            "CARGO_BUILD_JOBS": "2",
        }
        prepared = run(
            [str(cargo), "fetch", "--locked", "--manifest-path", str(directory / "Cargo.toml")],
            root,
            output / "dependencies.log",
            timeout=300,
            env=environment,
        )
        if prepared["status"] != "success":
            raise Invalid("The selected locked fuzz dependencies could not be prepared")
        environment["CARGO_NET_OFFLINE"] = "true"
        command = [
            str(cargo),
            "fuzz",
            "run",
            target,
            "--fuzz-dir",
            str(directory),
            "--target",
            triple,
            "--",
            str(owned_corpus),
            *arguments,
        ]
    elif engine == "libfuzzer":
        binary = contained(root, target, exists=True)
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise Invalid("Select an actual compiled native libFuzzer executable")
        command = [str(binary), str(owned_corpus), *arguments]
        version = "caller-built native libFuzzer; compiler identity belongs to its build stage"
    else:
        raise Invalid("Supported native fuzz engines: rust cargo-fuzz and libfuzzer")
    log = output / "fuzz.log"
    result = run(command, root, log, timeout=300 + seconds, env=environment)
    text = log.read_text()
    match = re.search(r"Done (\d+) runs", text)
    count = int(match[1]) if match else 0
    lock_changed = lock is not None and digest(lock) != before
    if result["status"] != "success" or count < 1 or lock_changed:
        result["status"] = "failure"
    result.update(
        source=source_identity(root),
        corpus_inputs=corpus_inputs,
        engine=engine,
        executions=count,
        compiler=version,
        lock_changed=lock_changed,
        failing_inputs=[str(p) for p in failures.iterdir() if p.is_file()],
    )
    atomic_json(output / "result.json", result)
    return result


def mutation(root: Path, output: Path, *, maximum_missed=0, timeout=15) -> dict:
    if (
        type(maximum_missed) is not int
        or maximum_missed < 0
        or type(timeout) is not int
        or not 1 <= timeout <= 300
    ):
        raise Invalid("Native mutation budgets must be explicit nonnegative/finite integers")
    output.mkdir(parents=True, exist_ok=False)
    result = run(
        [
            "cargo-mutants",
            "mutants",
            "--dir",
            str(root),
            "--output",
            str(output),
            "--jobs",
            "2",
            "--timeout",
            str(timeout),
            "--colors",
            "never",
        ],
        root,
        output / "mutation.log",
        timeout=900,
    )
    report = output / "mutants.out/outcomes.json"
    if not report.is_file() or report.stat().st_size > 64 * 1024**2:
        raise Invalid("Native cargo-mutants outcomes are missing or unbounded")
    outcomes = json.loads(report.read_text())
    counts = {key: outcomes.get(key) for key in ("total_mutants", "caught", "missed", "timeout", "unviable")}
    if any(type(x) is not int or x < 0 for x in counts.values()):
        raise Invalid("Native mutation counters are invalid")
    baseline = [x for x in outcomes.get("outcomes", []) if x.get("scenario") == "Baseline"]
    complete = counts["total_mutants"] == sum(
        counts[key] for key in ("caught", "missed", "timeout", "unviable")
    )
    success = (
        result["exit_code"] in {0, 2}
        and len(baseline) == 1
        and baseline[0].get("summary") == "Success"
        and complete
        and counts["caught"] + counts["missed"] > 0
        and counts["timeout"] == 0
        and counts["missed"] <= maximum_missed
    )
    result.update(
        status="success" if success else "failure",
        counts=counts,
        maximum_missed=maximum_missed,
        tool_version=outcomes.get("cargo_mutants_version"),
        source=source_identity(root),
    )
    atomic_json(output / "result.json", result)
    return result


def benchmark(baseline: Path, candidate: Path, maximum_ratio: float) -> dict:
    if not math.isfinite(maximum_ratio) or maximum_ratio <= 0:
        raise Invalid("Select an explicit positive finite benchmark regression budget")
    before, after = json.loads(baseline.read_text()), json.loads(candidate.read_text())

    def machine(document):
        info = document.get("machine_info", {})
        return [
            info.get("system"),
            info.get("machine"),
            info.get("python_version"),
            info.get("cpu", {}).get("brand_raw"),
        ]

    if not all(machine(before)) or machine(before) != machine(after):
        raise Invalid("Benchmark reports need the same actual identified machine/interpreter")

    def cases(document):
        values = {x["fullname"]: x["stats"] for x in document.get("benchmarks", [])}
        if not values or len(values) != len(document["benchmarks"]):
            raise Invalid("Native benchmark cases are missing or duplicated")
        for item in values.values():
            if (
                item.get("rounds", 0) < 1
                or not isinstance(item.get("median"), (float, int))
                or not math.isfinite(item["median"])
                or item["median"] <= 0
            ):
                raise Invalid("Native benchmark measurement is empty or invalid")
        return values

    if not before.get("version") or before["version"] != after.get("version"):
        raise Invalid("Benchmark tool versions must match the actual paired measurements")
    old, new = cases(before), cases(after)
    if old.keys() != new.keys():
        raise Invalid("Benchmark reports must identify exactly the same measured cases")
    ratios = {name: new[name]["median"] / old[name]["median"] for name in old}
    return {
        "status": "failure" if any(x > maximum_ratio for x in ratios.values()) else "success",
        "ratios": ratios,
        "maximum_ratio": maximum_ratio,
        "baseline_sha256": digest(baseline),
        "candidate_sha256": digest(candidate),
        "machine": machine(after),
        "tool_version": after["version"],
        "baseline_commit": before.get("commit_info"),
        "candidate_commit": after.get("commit_info"),
    }
