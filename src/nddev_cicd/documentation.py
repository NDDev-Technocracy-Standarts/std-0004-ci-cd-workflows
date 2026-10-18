"""Native text/link checks and canonical generation feedback, without prose attestations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

import yaml

from .model import Invalid, contained, git


class StrictLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    out = {}
    for key, value in node.value:
        name = loader.construct_object(key, deep=deep)
        if name in out:
            raise Invalid(f"Duplicate YAML key: {name}")
        out[name] = loader.construct_object(value, deep=deep)
    return out


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def check(root: Path, settings: dict | None = None) -> dict:
    settings = settings or {}
    exclusions = settings.get("exclude", [])
    paths = git(root, "ls-files", "-z").split("\0")
    checked, links = 0, 0
    for relative in paths:
        if not relative or any(Path(relative).match(pattern) for pattern in exclusions):
            continue
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        checked += 1
        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix in {".yml", ".yaml"}:
            list(yaml.load_all(text, Loader=StrictLoader))
        elif path.suffix == ".md":
            # Fence contents are executable examples/code data, not prose links.
            prose = re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", text)
            for match in re.finditer(r"(?<!!)\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)", prose):
                target = match.group(1).strip("<>")
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                destination = (path.parent / unquote(target.split("#", 1)[0])).resolve()
                if not destination.is_relative_to(root.resolve()) or not destination.exists():
                    raise Invalid(f"Broken/escaping local link: {relative} → {target}")
                links += 1
    if not checked:
        raise Invalid("Documentation selection matched no text files")
    return {
        "files": checked,
        "local_links": links,
        "external_links": "Use the selected external-link native command and explicit outage policy",
    }


def generation_clean(root: Path) -> None:
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise Invalid("Canonical generation changed the checkout (including untracked outputs)")


def external_outage(root: Path, settings: dict, operation: dict) -> dict | None:
    """Classify only explicitly scoped native Lychee timeouts; broken URLs remain failures."""
    report = settings.get("external_link_report")
    scoped = settings.get("network_timeouts", {})
    if operation.get("status") == "success" or not report or not scoped:
        return None
    payload = json.loads(contained(root, report, exists=True).read_text())
    if payload.get("errors") != 0 or payload.get("unknown") != 0 or not payload.get("timeouts"):
        return None
    records = [item for items in payload.get("timeout_map", {}).values() for item in items]
    if not records or len(records) != payload["timeouts"]:
        return None
    urls = sorted({item.get("url") for item in records})
    if any(url not in scoped or not isinstance(scoped[url], str) or not scoped[url] for url in urls):
        return None
    return {
        "status": "unavailable",
        "detail": "Scoped external transport timeout; URL availability is not established",
        "advisory_outage": {
            "native_reporter": "lychee",
            "urls": urls,
            "issue_refs": sorted({scoped[url] for url in urls}),
        },
    }
