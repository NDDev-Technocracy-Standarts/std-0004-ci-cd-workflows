"""Standard-library-only admission shared by bootstrap and the installed runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


class InvalidNativeCache(ValueError):
    """The explicitly selected native owner cannot be admitted."""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def admit_environment(environment: dict) -> tuple[dict, dict] | None:
    """Admit explicitly selected, digest-pinned native frontends without a second cache owner."""
    selected = environment.get("NDDEV_CACHE_PROVIDER")
    if not selected:
        return None
    if selected != "nds":
        raise InvalidNativeCache("Unsupported native cache provider")
    if os.name == "nt":
        raise InvalidNativeCache("The selected NDS managed cache provider is qualified for Linux and macOS")
    paths = []
    for key in ("NDS_CLEANER_BIN", "NDS_CLEANER_CONFIG"):
        value = environment.get(key)
        expected = environment.get(key + "_SHA256")
        if (
            not isinstance(value, str)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
        ):
            raise InvalidNativeCache(
                "NDS cache requires explicit binary/configuration paths and SHA-256 pins"
            )
        path = Path(value)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise InvalidNativeCache("NDS cache binary/configuration does not match its admitted pin")
        if key == "NDS_CLEANER_CONFIG" and path.stat().st_size > 16384:
            raise InvalidNativeCache("NDS cache configuration is not bounded")
        if digest(path) != expected:
            raise InvalidNativeCache("NDS cache binary/configuration does not match its admitted pin")
        paths.append(path)
    binary, config = paths
    try:
        settings = json.loads(config.read_text())
        root = Path(settings["root"])
        prefix = Path(settings["frontends"])
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidNativeCache("NDS cache configuration is invalid") from error
    retention = settings.get("retention_seconds")
    if (
        settings.get("schema") != 1
        or type(retention) is not int
        or not 86400 <= retention <= 365 * 86400
        or retention % 86400
    ):
        raise InvalidNativeCache("NDS cache requires an explicit supported whole-day idle policy")
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
        raise InvalidNativeCache("NDS cache root has no matching native ownership marker")
    if os.name != "nt" and (root.stat().st_uid != os.geteuid() or root.stat().st_mode & 0o077):
        raise InvalidNativeCache("NDS cache root must belong privately to this execution account")
    if (
        not prefix.is_absolute()
        or prefix.is_symlink()
        or prefix.resolve() != prefix
        or not prefix.is_dir()
        or str(prefix) != environment.get("NDS_CACHE_FRONTENDS")
    ):
        raise InvalidNativeCache("NDS cache frontend prefix differs from its admitted configuration")
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
            raise InvalidNativeCache("NDS cache frontends differ from the selected native owner")
    try:
        version = subprocess.check_output(
            [str(binary), "--version"], text=True, env=environment, timeout=30
        ).strip()
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise InvalidNativeCache(
            "Selected NDS cache owner could not identify its qualified protocol"
        ) from error
    if version != "nds-cleaner-cache 0.0.1-alpha.5":
        raise InvalidNativeCache("NDS cache artifact has no qualified protocol selection")
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


if __name__ == "__main__":
    try:
        if sys.argv[1:] != ["uv"]:
            raise InvalidNativeCache("Expected the native uv bootstrap selection")
        selection = admit_environment(dict(os.environ))
        if selection is None:
            raise InvalidNativeCache("Native bootstrap requires an explicit cache provider")
        print(str(Path(os.environ["NDS_CACHE_FRONTENDS"]) / "uv"))
    except (InvalidNativeCache, OSError, UnicodeError) as error:
        print(f"Native cache bootstrap unavailable: {error}", file=sys.stderr)
        sys.exit(2)
