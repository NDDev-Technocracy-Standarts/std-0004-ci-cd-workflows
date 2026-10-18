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
        "delivery",
    }
    if config.get("schema") != 1 or set(config) - allowed:
        raise Invalid("Unsupported project contract version or unknown fields")
    profiles = config.get("profiles", [])
    if not profiles or not all(isinstance(x, str) for x in profiles) or len(set(profiles)) != len(profiles):
        raise Invalid("Select a nonempty unique profile list")
    config["_path"] = relative
    return config


def catalog() -> dict:
    return json.loads(Path(__file__).with_name("profiles.json").read_text(encoding="utf-8"))
