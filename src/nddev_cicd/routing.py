"""Pre-scheduling, capability-aware no-charge admission. No billing API or quota daemon."""

from __future__ import annotations

from .model import Invalid, Unavailable

PLATFORMS = {"linux", "windows", "macos"}
STANDARD = {"linux": "ubuntu-24.04", "windows": "windows-2025", "macos": "macos-15"}


def select(
    visibility: str,
    platform: str,
    *,
    private_labels: list[str] | None = None,
    trusted: bool = False,
    architecture: str = "x64",
    admission: dict | None = None,
) -> dict:
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
        return {"provider": "self-hosted", "runner": labels, "basis": "existing-private-capacity"}
    choices = admission or {}
    for provider in ("blacksmith", "github"):
        policy = choices.get(provider, {})
        if not policy.get("enabled"):
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
