"""Execute selected native profiles; aggregate every required operation exactly once."""

from __future__ import annotations

import copy
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config, documentation, reports
from .model import Invalid, atomic_json, contained, digest, identity, source_identity
from .process import run


def selection(root: Path, contract: dict) -> tuple[list[str], dict | None]:
    selected = list(contract["profiles"])
    impact_record = None
    if contract.get("impact"):
        from .impact import affected

        specification = contract["impact"]
        components = specification.get("components", {})
        if not components or any(not item.get("profiles") for item in components.values()):
            raise Invalid("Every impact component requires explicit native profiles")
        source = source_identity(root)
        shared = list(specification.get("shared", [])) + [
            contract["_path"],
            "**/*lock*",
            "go.sum",
            ".github/workflows/*",
        ]
        chosen = affected(
            root, source.get("base") or "missing-base", source["tested_revision"], components, shared
        )
        selected = sorted(set(selected) | {p for name in chosen for p in components[name]["profiles"]})
        impact_record = {
            "base": source.get("base"),
            "selected_components": chosen,
            "not_applicable": {
                name: "No changed declared input or dependent" for name in components if name not in chosen
            },
        }

    return selected, impact_record


def _execute(root: Path, contract: dict, output: Path) -> dict:
    profiles = config.catalog()
    selected, impact_record = selection(root, contract)
    unknown = set(selected) - profiles.keys()
    if unknown:
        raise Invalid(f"Unsupported selected profiles: {sorted(unknown)}")
    output.mkdir(parents=True, exist_ok=True)
    (root / ".nddev-reports").mkdir(exist_ok=True)
    result = {
        "schema": 1,
        "identity": source_identity(root),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "selection": selected,
        "results": [],
        "expected": [],
    }
    result["impact"] = impact_record
    result["identity"]["contract_sha256"] = digest(contained(root, contract["_path"], exists=True))
    result["identity"]["locks"] = {
        path: digest(root / path)
        for path in (
            "uv.lock",
            "Cargo.lock",
            "package-lock.json",
            "pnpm-lock.yaml",
            "go.sum",
            "composer.lock",
            "Gemfile.lock",
            "packages.lock.json",
            "pubspec.lock",
            "renv.lock",
        )
        if (root / path).is_file()
    }
    commands = contract.get("commands", {})
    env = {str(key): str(value) for key, value in contract.get("environment", {}).items()}
    if any(key in env for key in ("GITHUB_TOKEN", "GH_TOKEN", "ACTIONS_RUNTIME_TOKEN")):
        raise Invalid("Credentials are not project contract values")
    env["NDDEV_RESULT_DIR"] = str(output.resolve())
    for tool, specification in contract.get("tools", {}).items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", tool) or not isinstance(specification, dict):
            raise Invalid("Tool identities require bounded names and explicit native version checks")
        command, pattern = specification.get("command"), specification.get("pattern")
        if not command or not isinstance(pattern, str) or not pattern:
            raise Invalid("Each tool requires its native version command and expected version pattern")
        name = "tool." + tool
        result["expected"].append(name)
        item = run(command, root, output / f"{name}.log", timeout=60, env=env)
        if item["status"] == "success" and not re.search(pattern, Path(item["log"]).read_text()):
            item.update(status="failure", detail="Executed tool version differs from selected contract")
        result["results"].append({"name": name, **item})
    cancelled = False
    for profile_id in selected:
        definition = profiles[profile_id]
        manifests = definition.get("manifests", [])
        if manifests and not any(list(root.glob(pattern)) for pattern in manifests):
            raise Invalid(f"{profile_id} has no matching native manifest: {manifests}")
        stage_status = {}
        setup_failed = any(
            i["status"] != "success" for i in result["results"] if i["name"].startswith("tool.")
        )
        for stage, default in definition["stages"].items():
            name = f"{profile_id}.{stage}"
            result["expected"].append(name)
            entry: dict = {"name": name, "status": "failure"}
            report = {}
            result["results"].append(entry)
            stage_status[stage] = entry
            # Write expected/results incrementally so interruptions never yield a complete green report.
            result["status"] = "failure"
            atomic_json(output / "result.json", result)
            try:
                if cancelled or setup_failed:
                    entry.update(
                        status="unavailable",
                        detail="Execution cancelled"
                        if cancelled
                        else "Required profile setup did not succeed",
                    )
                    continue
                dependencies = definition.get("dependencies", {}).get(stage, [])
                if any(stage_status.get(parent, {}).get("status") != "success" for parent in dependencies):
                    entry.update(status="unavailable", detail="Required native prerequisite did not succeed")
                    continue
                if stage == "syntax" and profile_id == "documentation":
                    entry.update(documentation.check(root, contract.get("documentation")), status="success")
                    continue
                if profile_id == "architecture" and stage == "scope":
                    scopes = contract.get("architecture", {}).get("scopes", [])
                    if not scopes or any(
                        not list(contained(root, scope, exists=True).rglob("*")) for scope in scopes
                    ):
                        raise Invalid("Architecture needs existing nonempty module scopes")
                    entry.update(status="success", scopes=scopes)
                    continue
                command = commands.get(profile_id, {}).get(stage, default)
                if isinstance(command, list) and command and command[0] == "@library":
                    helper = command[1]
                    command = [sys.executable, "-m", "nddev_cicd", helper, "--root", str(root)]
                    if helper == "package-check":
                        command += ["--contract", contract["_path"]]
                if command is None:
                    raise Invalid(f"Selected {name} requires a native project command")
                if stage == "test":
                    # Old reports cannot make a no-op test command green.
                    report = contract.get("reports", {}).get(profile_id, definition.get("report", {}))
                    reports.fresh(root, report)
                entry.update(
                    run(
                        command,
                        root,
                        output / f"{name}.log",
                        timeout=contract.get("timeouts", {}).get(profile_id, 900),
                        env=env,
                    )
                )
                if (
                    entry["status"] == "success"
                    and stage in definition.get("empty_output", [])
                    and command == default
                    and Path(entry["log"]).read_text().strip()
                ):
                    raise Invalid(f"{name} reported source formatting drift")
                if entry.get("detail") == "cancelled":
                    cancelled = True
                if stage == "setup" and entry["status"] != "success":
                    setup_failed = True
                if entry["status"] == "success" and stage == "test":
                    entry["tests_executed"] = reports.tests(root, report, Path(entry["log"]))
                if (
                    entry["status"] == "success"
                    and profile_id == "rust"
                    and stage == "build"
                    and command == default
                ):
                    from .rust import retain_package

                    entry["final_packages"] = retain_package(root, env)
                if entry["status"] == "success" and stage == "generate":
                    documentation.generation_clean(root)
            except (Invalid, ValueError, OSError, subprocess.SubprocessError) as error:
                entry.update(status="failure", detail=str(error))
    for name, extra in contract.get("extras", {}).items():
        if not isinstance(extra, dict) or not extra.get("command") or not extra.get("purpose"):
            raise Invalid("Each selected extra needs a concrete purpose, command and finite timeout")
        result["expected"].append("extra." + name)
        if extra.get("report"):
            reports.fresh(root, extra["report"])
        if cancelled:
            item: dict = {"status": "unavailable", "detail": "Execution cancelled"}
        else:
            item = run(
                extra["command"],
                root,
                output / f"extra-{name}.log",
                timeout=extra.get("timeout", 600),
                env=env,
            )
        if item["status"] == "success" and extra.get("report"):
            try:
                item["tests_executed"] = reports.tests(root, extra["report"], Path(item["log"]))
            except (Invalid, ValueError, OSError, subprocess.SubprocessError) as error:
                item.update(status="failure", detail=str(error))
        result["results"].append({"name": "extra." + name, **item})
    result.update(reports.aggregate(result["expected"], result["results"]))
    result["inputs_digest"] = identity(result["identity"])
    atomic_json(output / "result.json", result)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write("\n| Native check | Result |\n|---|---|\n")
            for entry in result["results"]:
                stream.write(f"| {entry['name']} | {entry['status']} |\n")
    return result


def execute(root: Path, contract: dict, output: Path) -> dict:
    contract = copy.deepcopy(contract)
    cache_root = os.environ.get("NDDEV_CACHE_ROOT")
    if "rust" not in selection(root, contract)[0] or not cache_root:
        return _execute(root, contract, output)
    from .cache import namespace, reclaim

    policy = contract.get("rust", {})
    budget, reserve, ttl = (
        policy.get(k) for k in ("cache_budget_bytes", "cache_min_free_bytes", "cache_ttl_seconds")
    )
    if (
        any(type(value) is not int for value in (budget, reserve, ttl))
        or budget < 1024 * 1024
        or reserve < 0
        or ttl < 1
    ):
        raise Invalid("Owned Rust caches require explicit byte budget, free-disk reserve and positive TTL")
    environment = {**os.environ, **{str(k): str(v) for k, v in contract.get("environment", {}).items()}}
    inputs = {
        "repository": os.environ.get("GITHUB_REPOSITORY", str(root.resolve())),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "trust": os.environ.get("NDDEV_TRUST_SCOPE", "local"),
        "configuration": {"rust": policy, "contract": digest(root / contract["_path"])},
        "toolchain": subprocess.check_output(["rustc", "-vV"], cwd=root, env=environment, text=True).strip(),
        "compiler_environment": {
            key: environment.get(key, "")
            for key in (
                "RUSTFLAGS",
                "CARGO_ENCODED_RUSTFLAGS",
                "RUSTUP_TOOLCHAIN",
                "CC",
                "CXX",
                "CFLAGS",
                "CXXFLAGS",
                "CARGO_BUILD_TARGET",
            )
        },
        "lock": digest(root / "Cargo.lock") if (root / "Cargo.lock").exists() else "missing",
    }
    storage = Path(cache_root)
    try:
        with namespace(storage, inputs) as owned:
            reclaim(storage, budget, reserve, ttl)
            if shutil.disk_usage(storage).free < reserve:
                raise Invalid("Available disk is below the owner's reserve after inactive cache reclamation")
            env = contract.setdefault("environment", {})
            env["CARGO_TARGET_DIR"], env["CARGO_HOME"] = str(owned / "target"), str(owned / "downloads")
            if not policy.get("sccache"):
                return _execute(root, contract, output)
            if os.name == "nt":
                raise Invalid(
                    "Local sccache ownership currently requires a Unix socket; native Cargo cache remains available"
                )
            active = owned / ".sccache-active.json"
            if active.exists():
                raise Invalid("An earlier sccache server needs owner reconciliation before reusing its store")
            # A short owned socket path avoids Unix socket limits on long runner/checkouts.
            socket_directory = Path(tempfile.mkdtemp(prefix="nddev-sc-"))
            env.update(
                {
                    "RUSTC_WRAPPER": "sccache",
                    "CARGO_INCREMENTAL": "0",
                    "SCCACHE_DIR": str(owned / "compiler"),
                    "SCCACHE_CACHE_SIZE": str(min(budget // 2, 2 * 1024**3)),
                    "SCCACHE_SERVER_UDS": str(socket_directory / "server.sock"),
                }
            )
            atomic_json(active, {"socket": env["SCCACHE_SERVER_UDS"], "owner": "nddev-cicd"})
            started = run(
                ["sccache", "--start-server"], root, output / "sccache-start.log", timeout=60, env=env
            )
            result = None
            try:
                if started["status"] != "success":
                    raise Invalid(
                        "Owned sccache server could not start; its store stays protected for reconciliation"
                    )
                result = _execute(root, contract, output)
            finally:
                statistics = run(
                    ["sccache", "--show-stats", "--stats-format=json"],
                    root,
                    output / "sccache-stats.log",
                    timeout=60,
                    env=env,
                )
                stopped = run(
                    ["sccache", "--stop-server"], root, output / "sccache-stop.log", timeout=60, env=env
                )
                if stopped["status"] == "success":
                    active.unlink()
                    shutil.rmtree(socket_directory)
                if result is not None:
                    entries = [
                        {"name": "cache.start", **started},
                        {"name": "cache.statistics", **statistics},
                        {"name": "cache.stop", **stopped},
                    ]
                    result["expected"].extend(item["name"] for item in entries)
                    result["results"].extend(entries)
                    result.update(reports.aggregate(result["expected"], result["results"]))
                    atomic_json(output / "result.json", result)
            if result is None:
                raise Invalid("Native cache execution produced no completed result")
            return result
    finally:
        if (storage / ".nddev-cache-owner.json").is_file():
            reclaim(storage, budget, reserve, ttl)
