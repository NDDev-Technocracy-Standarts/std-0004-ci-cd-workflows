"""Small project contract; native manifests/locks and explicit trusted commands own facts."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from .model import Invalid, contained


def load(root: Path, relative: str = ".github/nddev-ci.toml") -> dict:
    path = contained(root, relative, exists=True)
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    allowed = {
        "schema",
        "profiles",
        "commands",
        "reports",
        "tools",
        "extras",
        "documentation",
        "architecture",
        "artifacts",
        "timeouts",
        "environment",
        "package",
        "rust",
        "impact",
    }
    if type(config.get("schema")) is not int or config.get("schema") != 1 or set(config) - allowed:
        raise Invalid("Unsupported project contract version or unknown fields")
    profiles = config.get("profiles", [])
    if (
        not isinstance(profiles, list)
        or not profiles
        or not all(isinstance(x, str) for x in profiles)
        or len(set(profiles)) != len(profiles)
    ):
        raise Invalid("Select a nonempty unique profile list")
    if set(config.get("package", {})) - {"directory", "imports"}:
        raise Invalid("Unsupported package consumer setting")
    if set(config.get("rust", {})) - {
        "sccache",
        "cache_budget_bytes",
        "cache_min_free_bytes",
        "cache_ttl_seconds",
    }:
        raise Invalid("Unsupported Rust cache setting; native feature/MSRV commands belong in stages/extras")
    definitions = catalog()
    for profile, commands in config.get("commands", {}).items():
        if (
            profile not in definitions
            or not isinstance(commands, dict)
            or set(commands) - definitions[profile]["stages"].keys()
        ):
            raise Invalid(f"Unknown profile/native stage override: {profile}")
    config["_path"] = relative
    return config


def catalog() -> dict:
    return json.loads(Path(__file__).with_name("profiles.json").read_text(encoding="utf-8"))
