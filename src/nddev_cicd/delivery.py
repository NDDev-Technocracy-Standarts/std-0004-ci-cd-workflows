"""Native target adapters under one target lock; partial failure remains explicit."""

from __future__ import annotations

import json
import os
import plistlib
import re
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path

import yaml

from .artifacts import unpack, verify
from .cache import lock
from .model import Invalid, atomic_json, contained, digest, identity

MODULES = {"static-web", "systemd-binary", "compose", "packages", "mobile-artifacts"}


def mobile_format(path: Path) -> dict:
    """Inspect native mobile packaging, separately from signing or store authorization."""
    if path.suffix == ".xcarchive" and path.is_dir():
        metadata = plistlib.loads((path / "Info.plist").read_bytes())
        if not metadata.get("ApplicationProperties") or not list(
            path.glob("Products/Applications/*.app/Info.plist")
        ):
            raise Invalid("XCArchive has no native application metadata")
        return {"format": "xcarchive", "signing": "not-verified"}
    if not path.is_file() or path.suffix not in {".apk", ".aab", ".ipa"}:
        raise Invalid("Select a native APK, AAB, IPA or contained XCArchive")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
                raise Invalid("Mobile package contains an escaping member")
            if path.suffix in {".apk", ".aab"}:
                name = "AndroidManifest.xml" if path.suffix == ".apk" else "base/manifest/AndroidManifest.xml"
                if not 0 < archive.getinfo(name).file_size <= 16 * 1024 * 1024:
                    raise Invalid("Android package has no bounded native manifest")
                archive.read(name)  # Validate the actual native manifest bytes and ZIP CRC.
            else:
                entries = [name for name in names if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", name)]
                if len(entries) != 1 or archive.getinfo(entries[0]).file_size > 1024 * 1024:
                    raise Invalid("IPA has no unique bounded native application metadata")
                metadata = plistlib.loads(archive.read(entries[0]))
                executable = metadata.get("CFBundleExecutable")
                if (
                    not metadata.get("CFBundleIdentifier")
                    or not isinstance(executable, str)
                    or "/" in executable
                ):
                    raise Invalid("IPA application identity/executable is unavailable")
                if archive.getinfo(str(Path(entries[0]).parent / executable)).file_size <= 0:
                    raise Invalid("IPA application executable is empty")
    except (zipfile.BadZipFile, KeyError, ValueError) as error:
        raise Invalid("Mobile file is not the declared native package") from error
    return {"format": path.suffix.lstrip("."), "signing": "not-verified"}


def native(arguments: list[str], cwd: Path) -> None:
    subprocess.run(arguments, cwd=cwd, stdin=subprocess.DEVNULL, check=True, timeout=300)


def health(config: dict, revision: str) -> dict:
    url = config.get("health_url")
    if not url or not url.startswith(("http://", "https://")):
        raise Invalid("A meaningful target health URL is required for a running target")
    expected = config.get("health_contains", revision).replace("{revision}", revision)
    version_url = config.get("version_url", url)
    if not isinstance(version_url, str) or not version_url.startswith(("http://", "https://")):
        raise Invalid("Use a native HTTP version endpoint for the tested artifact")
    for attempt in range(10):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read(1024 * 1024).decode("utf-8")
                scenario_ok = response.status == 200 and expected in body
            if version_url == url:
                version_ok = revision in body
            else:
                with urllib.request.urlopen(version_url, timeout=5) as response:
                    version_ok = response.status == 200 and revision in response.read(1024 * 1024).decode(
                        "utf-8"
                    )
            if scenario_ok and version_ok:
                return {"url": url, "version_url": version_url, "status": 200, "matched_revision": revision}
        except (OSError, ValueError):
            pass
        if attempt != 9:
            time.sleep(0.2)
    raise Invalid("Target scenario/version did not match the intended tested revision")


def activate(root: Path, release: Path) -> None:
    current = root / "current"
    if current.exists() and not current.is_symlink():
        raise Invalid("Do not replace an unowned target directory")
    pending = root / f".current-{os.getpid()}"
    pending.symlink_to(release, target_is_directory=True)
    os.replace(pending, current)


def compose_state(config: dict, release: Path) -> list[str]:
    """Verify selected running services and their actual immutable image references without mutation."""
    compose = contained(release, config.get("compose_file", "compose.yaml"), exists=True)
    services = yaml.safe_load(compose.read_text())["services"]
    output = subprocess.check_output(
        [
            "docker",
            "compose",
            "--project-name",
            config["project"],
            "--file",
            str(compose),
            "ps",
            "--all",
            "--format",
            "json",
        ],
        text=True,
        timeout=30,
    ).strip()
    rows = (
        json.loads(output) if output.startswith("[") else [json.loads(line) for line in output.splitlines()]
    )
    selected = config["services"]
    for name in selected:
        actual = [row for row in rows if row.get("Service") == name]
        if not actual or any(
            row.get("State") != "running" or row.get("Health") not in {"", "healthy"} for row in actual
        ):
            raise Invalid("Selected Compose services are not actually running/healthy")
        for row in actual:
            installed = json.loads(
                subprocess.check_output(["docker", "inspect", row["ID"]], text=True, timeout=30)
            )[0]
            if installed["Config"]["Image"] != services[name]["image"]:
                raise Invalid("Running Compose image differs from the tested immutable configuration")
    return selected


def apply(archive: Path, manifest: dict, expected: dict, config: dict, *, authorized: bool) -> dict:
    if not authorized:
        raise Invalid("Target mutation requires an actual authorized trusted delivery context")
    module = config.get("module")
    if module not in MODULES:
        raise Invalid("Unsupported native delivery module")
    common = {
        "module",
        "target_directory",
        "generation",
        "expected_previous",
        "backup_command",
        "data_migration",
        "backup_waiver",
        "rollback_compatible",
        "recover_partial",
        "reconcile_command",
    }
    fields = {
        "static-web": {"entrypoint", "health_url", "health_contains", "version_url"},
        "systemd-binary": {"service", "user_service", "health_url", "health_contains", "version_url"},
        "compose": {"compose_file", "services", "project", "health_url", "health_contains", "version_url"},
        "packages": {"publisher", "package_file", "registry"},
        "mobile-artifacts": {"mobile_files"},
    }
    if set(config) - common - fields[module]:
        raise Invalid("Unknown or inapplicable native target setting")
    target_name = config.get("target_directory")
    if not isinstance(target_name, str) or not target_name.strip() or not Path(target_name).is_absolute():
        raise Invalid("Use an explicit absolute existing target directory")
    if "expected_previous" not in config:
        raise Invalid("Declare the expected previous target identity, including null on first delivery")
    declared_target = Path(target_name)
    target = declared_target.resolve()
    if not target.is_dir() or declared_target.is_symlink():
        raise Invalid("Use an explicitly existing owned non-symlink target")
    generation = config.get("generation")
    if type(generation) is not int or generation < 1:
        raise Invalid("Target generation is an explicit monotonic target-owner value, not a run ID")
    verify(archive, manifest, expected)
    revision = manifest["source"]["tested_revision"]
    artifact = manifest["artifact_identity"]
    target_contract = identity(
        {
            key: config[key]
            for key in (
                "module",
                "target_directory",
                "entrypoint",
                "service",
                "user_service",
                "compose_file",
                "services",
                "project",
                "publisher",
                "package_file",
                "registry",
                "mobile_files",
            )
            if key in config
        }
    )
    with lock(target / ".nddev-deploy.lock"):
        state_path = target / ".nddev-deployment.json"
        state = (
            json.loads(state_path.read_text()) if state_path.exists() else {"generation": 0, "artifact": None}
        )
        if state.get("pending"):
            if (
                not config.get("recover_partial")
                or state.get("artifact") != artifact
                or state.get("generation") != generation
            ):
                raise Invalid(
                    "Previous delivery is partial; explicitly reconcile the same artifact/generation"
                )
            if state.get("module") != module:
                raise Invalid("Recovery module differs from the pending target")
            if state.get("target_contract") != target_contract:
                raise Invalid("Recovery cannot retarget the pending native operation")
            release = target / ".nddev-releases" / artifact
            for name, entry in manifest["files"].items():
                actual = contained(release, name, exists=True)
                if digest(actual) != entry["sha256"] or actual.stat().st_mode & 0o777 != entry["mode"]:
                    raise Invalid("Pending installed artifact bytes/modes differ")
            if module in {"static-web", "systemd-binary"} and (target / "current").resolve() != release:
                raise Invalid("Current files differ; complete target recovery outside this retry")
            if module in {"static-web", "systemd-binary", "compose"}:
                if module == "compose":
                    state["services"] = compose_state(config, release)
                state["health"] = health(config, revision)
            else:
                if module == "mobile-artifacts":
                    for relative in config["mobile_files"]:
                        mobile_format(contained(release, relative, exists=True))
                verification = config.get("reconcile_command")
                if not verification:
                    raise Invalid(
                        "Registry/mobile partial recovery needs an explicit native verification command"
                    )
                native(verification, release)
            state.update(
                pending=False, status="success", recovery="actual installed artifact and target verified"
            )
            atomic_json(state_path, state)
            return state
        if state["generation"] >= generation or config.get("expected_previous") != state.get("artifact"):
            raise Invalid("Stale deployment or changed previous target; do not overwrite newer state")
        if (
            config.get("data_migration")
            and not config.get("backup_command")
            and not config.get("backup_waiver")
        ):
            raise Invalid("Data mutation requires existing recovery or an explicit scoped backup waiver")
        if config.get("data_migration") and not config.get("backup_command"):
            waiver = config.get("backup_waiver")
            if (
                not isinstance(waiver, dict)
                or waiver.get("target") != str(target)
                or not isinstance(waiver.get("reason"), str)
                or len(waiver["reason"]) < 10
                or not isinstance(waiver.get("reference"), str)
                or not waiver["reference"]
            ):
                raise Invalid(
                    "A backup waiver needs this exact target, an actual reason and its owner decision reference"
                )
        releases = target / ".nddev-releases"
        if releases.is_symlink() or (
            releases.exists()
            and (
                not (releases / ".nddev-owner").is_file()
                or (releases / ".nddev-owner").read_text() != "nddev-cicd/v1\n"
            )
        ):
            raise Invalid("Do not adopt an unowned release directory")
        releases.mkdir(exist_ok=True)
        (releases / ".nddev-owner").write_text("nddev-cicd/v1\n")
        release = releases / artifact
        if release.exists():
            raise Invalid("Existing incomplete release must be reconciled, not overwritten")
        unpack(archive, manifest, release, expected)
        previous = (target / "current").resolve() if (target / "current").is_symlink() else None
        record = {
            "generation": generation,
            "artifact": artifact,
            "revision": revision,
            "previous_artifact": state.get("artifact"),
            "pending": True,
            "module": module,
            "target_contract": target_contract,
            "previous_release": str(previous) if previous else None,
        }
        atomic_json(state_path, record)
        try:
            if config.get("backup_command"):
                native(config["backup_command"], target)
            if config.get("data_migration"):
                native(config["data_migration"], release)
            if module == "compose":
                compose = contained(release, config.get("compose_file", "compose.yaml"), exists=True)
                content = yaml.safe_load(compose.read_text())
                services = content.get("services", {})
                expected_services = config.get("services", [])
                if not expected_services or set(expected_services) - services.keys():
                    raise Invalid("Select actual nonempty Compose services")
                if any(
                    "build" in services[name]
                    or not re.search(r"@sha256:[0-9a-f]{64}$", services[name].get("image", ""))
                    for name in services
                ):
                    raise Invalid(
                        "Compose delivery requires built immutable image digests, not candidate builds"
                    )
                project = config.get("project")
                if not isinstance(project, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
                    raise Invalid("Compose needs an explicit stable project owner")
                native(
                    [
                        "docker",
                        "compose",
                        "--project-name",
                        project,
                        "--file",
                        str(compose),
                        "up",
                        "--detach",
                        "--wait",
                        "--no-build",
                        "--no-deps",
                        *expected_services,
                    ],
                    release,
                )
                record["services"] = compose_state(config, release)
            elif module == "systemd-binary":
                service = config.get("service", "")
                if not re.fullmatch(r"[A-Za-z0-9_.@-]+\.service", service):
                    raise Invalid("Select one actual systemd service")
                activate(target, release)
                command = ["systemctl"] + (["--user"] if config.get("user_service", True) else [])
                native([*command, "daemon-reload"], target)
                native([*command, "restart", service], target)
                native([*command, "is-active", "--quiet", service], target)
            elif module == "static-web":
                contained(release, config.get("entrypoint", "index.html"), exists=True)
                activate(target, release)
            elif module == "packages":
                publisher = config.get("publisher")
                package = contained(release, config["package_file"], exists=True)
                registry = config.get("registry")
                if not isinstance(registry, str) or not registry.startswith("https://"):
                    raise Invalid("Package publication needs an explicit existing HTTPS registry")
                if publisher == "python":
                    native(["uv", "publish", "--publish-url", registry, str(package)], release)
                elif publisher == "npm":
                    native(["npm", "publish", str(package), "--registry", registry], release)
                elif publisher == "nuget":
                    native(["dotnet", "nuget", "push", str(package), "--source", registry], release)
                else:
                    raise Invalid("Supported native publishers: python, npm, nuget")
            else:
                files = config.get("mobile_files", [])
                if not files:
                    raise Invalid("Select actual configured mobile deliverable files")
                record["mobile_packages"] = {}
                for relative in files:
                    record["mobile_packages"][relative] = mobile_format(
                        contained(release, relative, exists=True)
                    )
                record["boundary"] = "artifact-delivery; store submission not performed"
            if module in {"compose", "systemd-binary", "static-web"}:
                record["health"] = health(config, revision)
            record["pending"] = False
            record["status"] = "success"
            atomic_json(state_path, record)
            return record
        except BaseException as error:
            record["status"], record["failure"] = "failure", type(error).__name__
            # Do not roll back data to an incompatible previous binary or retry unknown partial state.
            if config.get("rollback_compatible") and not config.get("data_migration") and previous:
                activate(target, previous)
                record["recovery"] = (
                    "previous files restored; service/data health requires target reconciliation"
                )
            atomic_json(state_path, record)
            raise
