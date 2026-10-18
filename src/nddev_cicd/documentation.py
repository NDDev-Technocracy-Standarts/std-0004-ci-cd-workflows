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
        if not relative or any(
            Path(relative).match(pattern)
            or (pattern.endswith("/") and Path(relative).is_relative_to(pattern.rstrip("/")))
            for pattern in exclusions
        ):
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
    """Keep explicitly scoped native transport/access failures unavailable; broken URLs stay failures."""
    report = settings.get("external_link_report")
    if operation.get("status") == "success" or not report:
        return None
    payload = json.loads(contained(root, report, exists=True).read_text())
    if payload.get("unknown") != 0 or payload.get("unsupported", 0) != 0:
        return None
    timeouts = [item for items in payload.get("timeout_map", {}).values() for item in items]
    errors = [item for items in payload.get("error_map", {}).values() for item in items]
    if len(timeouts) != payload.get("timeouts", 0) or len(errors) != payload.get("errors", 0):
        return None
    if not timeouts and not errors:
        return None
    scoped_timeouts = {**settings.get("network_outages", {}), **settings.get("network_timeouts", {})}
    refs = []
    for item in timeouts:
        reference = scoped_timeouts.get(item.get("url"))
        if not isinstance(reference, str) or not reference:
            return None
        refs.append(reference)
    for item in errors:
        url, status = item.get("url"), item.get("status", {})
        code = status.get("code")
        if code is None and status.get("text", "").startswith("Network error:"):
            reference = settings.get("network_outages", {}).get(url)
        else:
            disposition = settings.get("access_outages", {}).get(url, {})
            # Never authorize a missing URL (404) or a general HTTP-error whitelist.
            if code not in {403, 429} or disposition.get("status") != code or not disposition.get("reason"):
                return None
            reference = disposition.get("issue")
        if not isinstance(reference, str) or not reference:
            return None
        refs.append(reference)
    return {
        "status": "unavailable",
        "detail": "Scoped native transport/access failure; URL availability is not established",
        "advisory_outage": {
            "native_reporter": "lychee",
            "urls": sorted({item["url"] for item in [*timeouts, *errors]}),
            "issue_refs": sorted(set(refs)),
        },
    }
