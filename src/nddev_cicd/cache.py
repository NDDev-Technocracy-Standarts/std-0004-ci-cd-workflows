"""Owned bounded local cache namespaces with native process locking."""

from __future__ import annotations

import contextlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from .model import Invalid, atomic_json, identity


def nds_environment(environment: dict) -> tuple[dict, dict] | None:
    """Admit explicitly selected, digest-pinned native frontends without a second cache owner."""
    selected = environment.get("NDDEV_CACHE_PROVIDER")
    if not selected:
        return None
    if selected != "nds":
        raise Invalid("Unsupported native cache provider")
    if os.name == "nt":
        raise Invalid("The selected NDS managed cache provider is qualified for Linux and macOS")
    from .model import digest

    paths = []
    for key in ("NDS_CLEANER_BIN", "NDS_CLEANER_CONFIG"):
        value = environment.get(key)
        expected = environment.get(key + "_SHA256")
        if (
            not isinstance(value, str)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
        ):
            raise Invalid("NDS cache requires explicit binary/configuration paths and SHA-256 pins")
        path = Path(value)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise Invalid("NDS cache binary/configuration does not match its admitted pin")
        if key == "NDS_CLEANER_CONFIG" and path.stat().st_size > 16384:
            raise Invalid("NDS cache configuration is not bounded")
        if digest(path) != expected:
            raise Invalid("NDS cache binary/configuration does not match its admitted pin")
        paths.append(path)
    binary, config = paths
    try:
        settings = json.loads(config.read_text())
        root = Path(settings["root"])
        prefix = Path(settings["frontends"])
    except (ValueError, TypeError, KeyError) as error:
        raise Invalid("NDS cache configuration is invalid") from error
    retention = settings.get("retention_seconds")
    if (
        settings.get("schema") != 1
        or type(retention) is not int
        or not 86400 <= retention <= 365 * 86400
        or retention % 86400
    ):
        raise Invalid("NDS cache requires an explicit supported whole-day idle policy")
    if (
        not root.is_absolute()
        or root.is_symlink()
        or root.resolve() != root
        or not root.is_dir()
        or (root / ".nds-cache").is_symlink()
        or not (root / ".nds-cache").is_file()
        or (root / ".nds-cache").stat().st_size > 128
        or (root / ".nds-cache").read_bytes() != b"NDS managed rebuildable cache v1\n"
    ):
        raise Invalid("NDS cache root has no matching native ownership marker")
    if os.name != "nt" and (root.stat().st_uid != os.geteuid() or root.stat().st_mode & 0o077):
        raise Invalid("NDS cache root must belong privately to this execution account")
    if (
        not prefix.is_absolute()
        or prefix.is_symlink()
        or prefix.resolve() != prefix
        or not prefix.is_dir()
        or str(prefix) != environment.get("NDS_CACHE_FRONTENDS")
    ):
        raise Invalid("NDS cache frontend prefix differs from its admitted configuration")
    for command in ("cargo", "uv", "bun"):
        path = prefix / command
        expected = (
            "#!/bin/sh\n# NDS managed development cache frontend\nexec "
            + shlex.join([str(binary), str(config), command])
            + ' "$@"\n'
        )
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > 16384
            or path.read_text() != expected
        ):
            raise Invalid("NDS cache frontends differ from the selected native owner")
    try:
        version = subprocess.check_output(
            [str(binary), "--version"], text=True, env=environment, timeout=30
        ).strip()
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise Invalid("Selected NDS cache owner could not identify its qualified protocol") from error
    if version != "nds-cleaner-cache 0.0.1-alpha.5":
        raise Invalid("NDS cache artifact has no qualified protocol selection")
    # Return only the preparation delta. Copying the callee's full environment
    # into the caller contract would reintroduce its UV_PROJECT_ENVIRONMENT.
    admitted = {"PATH": str(prefix) + os.pathsep + environment.get("PATH", "")}
    observation = {
        "schema": 1,
        "provider": "nds",
        "version": version,
        "binary_sha256": environment["NDS_CLEANER_BIN_SHA256"],
        "configuration_sha256": environment["NDS_CLEANER_CONFIG_SHA256"],
        "retention_seconds": retention,
        "managed_tools": ["cargo", "uv", "bun"],
        "collection": "external_owner",
        "hit_observed": False,
    }
    return admitted, observation


@contextlib.contextmanager
def lock(path: Path, *, blocking: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise Invalid("An owned lock cannot follow a symlink")
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            if not path.stat().st_size:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_UN)


@contextlib.contextmanager
def namespace(root: Path, inputs: dict, *, blocking: bool = True):
    if root.is_symlink():
        raise Invalid("A cache owner root cannot be a symlink")
    if (
        root.exists()
        and any(p.name != ".owner.lock" for p in root.iterdir())
        and not (root / ".nddev-cache-owner.json").is_file()
        # An initializer holds this lock before publishing its atomic marker.
        # Inspect that state under the lock, preserving write-free rejection of
        # foreign directories which have no existing ownership lock.
        and not (root / ".owner.lock").exists()
    ):
        raise Invalid("Do not adopt an existing unowned cache directory")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    owner = root / ".nddev-cache-owner.json"
    with lock(root / ".owner.lock"):
        if owner.exists() and json.loads(owner.read_text()) != {"schema": 1, "owner": "nddev-cicd"}:
            raise Invalid("Cache root belongs to another owner")
        if not owner.exists() and any(p.name != ".owner.lock" for p in root.iterdir()):
            raise Invalid("Do not adopt an existing unowned cache directory")
        atomic_json(owner, {"schema": 1, "owner": "nddev-cicd"})
    name = identity(inputs)
    path = root / name
    with lock(root / f"{name}.lock", blocking=blocking):
        if path.is_symlink():
            raise Invalid("Cache namespace cannot be a symlink")
        path.mkdir(exist_ok=True)
        atomic_json(path / "identity.json", inputs)
        os.utime(path, None)
        yield path


@contextlib.contextmanager
def compiler(root: Path, policy: dict, environment: dict, contract_path: str):
    """One bounded ccache namespace, with a native launcher and no daemon or host-wide prune."""
    from .model import digest

    values: list[int] = []
    for key in ("cache_budget_bytes", "cache_min_free_bytes", "cache_ttl_seconds"):
        value = policy.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise Invalid("Compiler caches require explicit byte budget, free-disk reserve and TTL")
        values.append(value)
    budget, reserve, ttl = values
    if budget < 1024**2 or reserve < 0 or ttl < 1:
        raise Invalid("Compiler cache budget/TTL must be positive and reserve nonnegative")
    location = os.environ.get("NDDEV_CCACHE_ROOT")
    if not location:
        raise Invalid("Selected compiler cache needs an owner-provided NDDEV_CCACHE_ROOT")
    storage = Path(location)
    if (
        not storage.is_absolute()
        or storage.resolve() == Path(os.environ.get("NDDEV_CACHE_ROOT", ".")).resolve()
    ):
        raise Invalid("Compiler and Cargo caches need separate absolute owner roots and budgets")
    process_environment = {**os.environ, **{str(k): str(v) for k, v in environment.items()}}
    executable = shutil.which("ccache", path=process_environment.get("PATH"))
    if not executable:
        raise Invalid("Selected compiler cache requires its actual native ccache tool")
    for key in ("CMAKE_C_COMPILER_LAUNCHER", "CMAKE_CXX_COMPILER_LAUNCHER"):
        if process_environment.get(key, "ccache") not in {"ccache", executable}:
            raise Invalid("Selected compiler cache conflicts with an existing native launcher")
    version = subprocess.check_output(
        [executable, "--version"], text=True, env=process_environment, timeout=30
    )
    inputs = {
        "kind": "ccache",
        "repository": os.environ.get("GITHUB_REPOSITORY", str(root.resolve())),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "toolchain": version.splitlines()[0],
        "trust": [os.environ.get("GITHUB_EVENT_NAME", "local"), os.environ.get("GITHUB_REF", "local")],
        "configuration": digest(root / contract_path),
    }
    try:
        with namespace(storage, inputs) as owned:
            reclaim(storage, budget, reserve, ttl)
            if shutil.disk_usage(storage).free < reserve:
                raise Invalid("Available disk is below the compiler cache owner's reserve")
            yield {
                "CCACHE_DIR": str(owned / "compiler"),
                "CCACHE_BASEDIR": str(root.resolve()),
                "CCACHE_MAXSIZE": str(max(1, budget // 1024**2 - 1)) + "Mi",
                "CCACHE_COMPILERCHECK": "content",
                "CMAKE_C_COMPILER_LAUNCHER": executable,
                "CMAKE_CXX_COMPILER_LAUNCHER": executable,
            }
    finally:
        if (storage / ".nddev-cache-owner.json").is_file():
            reclaim(storage, budget, reserve, ttl)


def size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())


def reclaim(root: Path, budget: int, min_free: int, ttl_seconds: int) -> list[str]:
    """Retain opaque compiler payloads until a pinned native Cleaner owns them.

    Namespace mtime, an unlocked library wrapper and storage pressure do not
    prove completed native use or the absence of an inherited child/pin. This
    compatibility entry point validates ownership without adopting/deleting
    legacy data. Admission still enforces the caller's free-space reserve.
    """
    if budget <= 0 or min_free < 0 or ttl_seconds < 1:
        raise Invalid("Explicit positive cache budget/TTL and available-disk reserve are required")
    owner = root / ".nddev-cache-owner.json"
    if (
        root.is_symlink()
        or not owner.exists()
        or owner.is_symlink()
        or json.loads(owner.read_text()) != {"schema": 1, "owner": "nddev-cicd"}
    ):
        raise Invalid("No matching cache owner; nothing reclaimed")
    return []
