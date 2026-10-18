"""Pre-scheduling, capability-aware no-charge admission. No billing API or quota daemon."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .model import Invalid, Unavailable

PLATFORMS = {"linux", "windows", "macos"}
STANDARD = {"linux": "ubuntu-24.04", "windows": "windows-2025", "macos": "macos-15"}


def caller_policy(policy: dict) -> dict:
    """A reusable publisher never changes the actual caller's billing/trust context."""
    result = dict(policy)
    actors = result.pop("trusted_actors", None)
    if actors is not None and (
        not isinstance(actors, list)
        or not actors
        or not all(isinstance(actor, str) and actor for actor in actors)
    ):
        raise Invalid("Trusted actors must be an explicit nonempty caller-owned list")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return result
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        repository = event["repository"]
        actual = repository.get("visibility")
        if actual == "internal":
            actual = "private"
        if actual is None and type(repository.get("private")) is bool:
            actual = "private" if repository["private"] else "public"
        if actual not in {"public", "private"} or repository["full_name"] != os.environ["GITHUB_REPOSITORY"]:
            raise Unavailable("The actual caller repository visibility cannot be established")
    except (KeyError, OSError, ValueError) as error:
        raise Unavailable("The actual caller repository context is unavailable") from error
    if policy.get("visibility") != actual:
        raise Invalid("Admission policy visibility differs from the actual caller repository")
    if "pull_request" in event:
        head = event["pull_request"].get("head", {}).get("repo") or {}
        association = event["pull_request"].get("author_association")
        actor_is_trusted = (
            (os.environ.get("GITHUB_ACTOR") in actors)
            if actors is not None
            else association in {"OWNER", "MEMBER", "COLLABORATOR"}
        )
        if head.get("full_name") != repository["full_name"] or not actor_is_trusted:
            result["trusted"] = False
    return result


def select(
    visibility: str,
    platform: str,
    *,
    private_labels: list[str] | None = None,
    trusted: bool = False,
    architecture: str = "x64",
    admission: dict | None = None,
) -> dict:
    if type(trusted) is not bool:
        raise Invalid("Trusted capacity selection requires a boolean owner policy")
    if visibility not in {"public", "private"} or platform not in PLATFORMS:
        raise Invalid("Unknown repository visibility or platform")
    if architecture not in {"x64", "arm64"}:
        raise Invalid("Unknown runner architecture")
    if platform == "linux":
        if visibility == "public":
            if architecture != "x64":
                raise Unavailable("Declare a verified standard public ARM runner separately")
            return {"provider": "github", "runner": [STANDARD[platform]], "basis": "standard-public"}
        if not trusted:
            raise Unavailable("Untrusted/fork code cannot schedule private self-hosted capacity")
        labels = private_labels or []
        if (
            not labels
            or "self-hosted" not in labels
            or not all(
                isinstance(label, str) and label and len(label) <= 100 and "\n" not in label
                for label in labels
            )
        ):
            raise Invalid("Private Linux requires bounded caller-owned self-hosted labels")
        actual = {label.casefold() for label in labels}
        if "linux" not in actual or architecture not in actual:
            raise Invalid(
                "Private labels must include the verified Linux and selected architecture capabilities"
            )
        return {"provider": "self-hosted", "runner": labels, "basis": "existing-private-capacity"}
    choices = admission or {}
    for provider in ("blacksmith", "github"):
        policy = choices.get(provider, {})
        if type(policy.get("enabled", False)) is not bool:
            raise Invalid("Capacity admission enabled must be a boolean")
        if not policy.get("enabled", False):
            continue
        # Caller-owned trusted account policy, never a PR balance/label or an email alert.
        if policy.get("guarantee") not in {"hard-no-overage", "standard-public"} or not policy.get(
            "reference"
        ):
            continue
        if policy.get("guarantee") == "standard-public" and (provider != "github" or visibility != "public"):
            continue
        if platform not in policy.get("platforms", []) or architecture not in policy.get("architectures", []):
            continue
        runner = policy.get("runners", {}).get(platform)
        if not isinstance(runner, list) or not runner or not all(isinstance(x, str) for x in runner):
            raise Invalid("Admission must resolve a known runner before scheduling")
        if policy.get("guarantee") == "standard-public" and (
            runner != [STANDARD[platform]] or architecture != ("arm64" if platform == "macos" else "x64")
        ):
            raise Invalid("Standard public admission cannot allocate larger or incompatible runners")
        return {"provider": provider, "runner": runner, "basis": policy["reference"]}
    if visibility == "public" and architecture == ("arm64" if platform == "macos" else "x64"):
        return {"provider": "github", "runner": [STANDARD[platform]], "basis": "standard-public"}
    raise Unavailable("No confirmed compatible no-overage route; paid-capable dispatch remains disabled")
