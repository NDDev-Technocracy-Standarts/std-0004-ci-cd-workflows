"""Free native security commands; callers own source scopes and license policy."""

from __future__ import annotations

import re
from pathlib import Path

from .impact import matches
from .model import Invalid, contained, git


def native_command(helper: str, root: Path, contract: dict) -> list[str]:
    settings = contract.get("security", {})
    if helper == "security-licenses":
        licenses = settings.get("licenses")
        if (
            not isinstance(licenses, list)
            or not licenses
            or any(
                not isinstance(x, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", x) for x in licenses
            )
        ):
            raise Invalid("Default license checking requires an explicit SPDX security.licenses allowlist")
        return ["osv-scanner", "scan", "source", "--recursive", "--licenses=" + ",".join(licenses), "."]
    scopes = settings.get("python")
    if (
        not isinstance(scopes, list)
        or not scopes
        or any(
            not isinstance(x, str) or not x or Path(x).is_absolute() or ".." in Path(x).parts for x in scopes
        )
    ):
        raise Invalid("Default Python SAST requires explicit security.python tracked source globs")
    tracked = [x for x in git(root, "ls-files", "-z").split("\0") if x.endswith(".py")]
    selected = set()
    for scope in scopes:
        found = [x for x in tracked if matches(x, scope)]
        if not found:
            raise Invalid("Python SAST scope has no tracked source: " + scope)
        for relative in found:
            if (root / relative).is_symlink() or not contained(root, relative, exists=True).is_file():
                raise Invalid("Python SAST requires contained regular source files")
        selected.update(found)
    return ["bandit", "--quiet", "--", *sorted(selected)]
