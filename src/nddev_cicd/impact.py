"""Conservative affected-component closure; uncertainty retains every selected obligation."""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

from .model import Invalid


def affected(root: Path, base: str, head: str, components: dict, shared: list[str]) -> list[str]:
    if not components or any(not value.get("paths") for value in components.values()):
        raise Invalid("Impact selection requires nonempty declared component scopes")
    for value in components.values():
        if set(value.get("depends_on", [])) - components.keys():
            raise Invalid("Unknown component dependency")
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "--no-renames", "-z", base, head],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        return sorted(components)
    paths = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    if any(PurePosixPath(path).match(pattern) for path in paths for pattern in shared):
        return sorted(components)
    selected = {
        name
        for name, value in components.items()
        if any(PurePosixPath(path).match(pattern) for path in paths for pattern in value["paths"])
    }
    if paths and not selected:
        return sorted(components)
    while True:
        additions = {
            name for name, value in components.items() if set(value.get("depends_on", [])) & selected
        }
        if additions <= selected:
            return sorted(selected)
        selected |= additions
