"""Tool, action and Python tool versions come from one lock generated from a technology registry.

The registry is the only place a version is written by hand. `tools-lock --registry PATH --write`
regenerates `.github/tools.lock.json`, the Python tool pins and every `uses:` commit from it.
`tools-lock --check` keeps this repository free of versions outside the lock.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
import urllib.request
from pathlib import Path

from .model import Invalid

LOCK = Path(".github/tools.lock.json")
SCRIPT = Path("scripts/prepare-linux-tools.sh")
GITHUB = "https://github.com"

# How each binary tool is fetched. Versions come from the registry, never from this table.
TOOLS = {
    "actionlint": ("archive", GITHUB + "/rhysd/actionlint/releases/download/v{v}/actionlint_{v}_linux_amd64.tar.gz"),
    "lychee": ("archive", GITHUB + "/lycheeverse/lychee/releases/download/lychee-v{v}/lychee-x86_64-unknown-linux-musl.tar.gz"),
    "zizmor": ("archive", GITHUB + "/zizmorcore/zizmor/releases/download/v{v}/zizmor-x86_64-unknown-linux-gnu.tar.gz"),
    "cargo-machete": (
        "archive",
        GITHUB + "/bnjbvr/cargo-machete/releases/download/v{v}/cargo-machete-v{v}-x86_64-unknown-linux-musl.tar.gz",
    ),
    "ccache": ("archive", GITHUB + "/ccache/ccache/releases/download/v{v}/ccache-{v}-linux-x86_64-musl-static.tar.gz"),
    "typos": ("archive", GITHUB + "/crate-ci/typos/releases/download/v{v}/typos-v{v}-x86_64-unknown-linux-musl.tar.gz"),
    "cargo-deny": (
        "archive",
        GITHUB + "/EmbarkStudios/cargo-deny/releases/download/{v}/cargo-deny-{v}-x86_64-unknown-linux-musl.tar.gz",
    ),
    "sccache": ("archive", GITHUB + "/mozilla/sccache/releases/download/v{v}/sccache-v{v}-x86_64-unknown-linux-musl.tar.gz"),
    "cargo-audit": (
        "archive",
        GITHUB + "/rustsec/rustsec/releases/download/cargo-audit%2Fv{v}/cargo-audit-x86_64-unknown-linux-musl-v{v}.tgz",
    ),
    "cargo-nextest": (
        "archive",
        GITHUB
        + "/nextest-rs/nextest/releases/download/cargo-nextest-{v}/cargo-nextest-{v}-x86_64-unknown-linux-musl.tar.gz",
    ),
    "gitleaks": ("archive", GITHUB + "/gitleaks/gitleaks/releases/download/v{v}/gitleaks_{v}_linux_x64.tar.gz"),
    "osv-scanner": ("file", GITHUB + "/google/osv-scanner/releases/download/v{v}/osv-scanner_linux_amd64"),
    "trufflehog": ("archive", GITHUB + "/trufflesecurity/trufflehog/releases/download/v{v}/trufflehog_{v}_linux_amd64.tar.gz"),
    "shellcheck": ("archive", GITHUB + "/koalaman/shellcheck/releases/download/v{v}/shellcheck-v{v}.linux.x86_64.tar.gz"),
    "bats-core": ("tree", "https://codeload.github.com/bats-core/bats-core/tar.gz/{commit}"),
    "trivy": ("archive", GITHUB + "/aquasecurity/trivy/releases/download/v{v}/trivy_{v}_Linux-64bit.tar.gz"),
    "hadolint": ("file", GITHUB + "/hadolint/hadolint/releases/download/v{v}/hadolint-linux-x86_64"),
}

# Python tools pinned in the library's own tool projects.
PYTHON = {
    ".github/native-tools/pyproject.toml": ("aqtinstall", "semgrep", "mutmut", "coverage", "pytest"),
    "tools/security/pyproject.toml": ("bandit",),
}

USES = re.compile(r"(uses: )([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)((?:/[A-Za-z0-9_./-]+)?)@([0-9a-f]{40})( # \S+)?")


def registry_lines(path: Path) -> dict[str, dict]:
    """The accepted line of every technology: its version and, for actions, its commit."""
    technologies = tomllib.loads(path.read_text()).get("technologies", {})
    return {name: entry["lines"][0] for name, entry in technologies.items() if entry.get("lines")}


def _sha256(url: str) -> str:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "nddev-cicd-tools-lock"})
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 - fixed https sources
        for chunk in iter(lambda: response.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(root: Path, registry: Path) -> dict:
    """Generate the lock from the registry, reusing checksums of unchanged downloads."""
    lines = registry_lines(registry)
    previous = json.loads((root / LOCK).read_text()) if (root / LOCK).is_file() else {}
    tools = {}
    for name, (kind, template) in TOOLS.items():
        line = lines.get(name)
        if not line:
            raise Invalid(f"The registry has no line for tool {name}")
        url = template.format(v=line["version"], commit=line.get("commit", ""))
        known = previous.get("tools", {}).get(name, {})
        sha = known["sha256"] if known.get("url") == url and known.get("sha256") else _sha256(url)
        tools[name] = {"version": line["version"], "kind": kind, "url": url, "sha256": sha}
    python = {}
    for project, names in PYTHON.items():
        for name in names:
            line = lines.get(name)
            if not line:
                raise Invalid(f"The registry has no line for Python tool {name}")
            python[name] = line["version"]
    actions = {}
    for workflow in _workflow_files(root):
        for match in USES.finditer(workflow.read_text()):
            repository = match.group(2)
            if repository.startswith("NDDev-Technocracy-Standarts/"):
                continue
            line = lines.get(repository)
            if not line or not line.get("commit"):
                raise Invalid(f"The registry has no pinned line for action {repository}")
            actions[repository] = {"version": line["version"], "commit": line["commit"]}
    return {
        "generated_from": "technology registry",
        "tools": tools,
        "python": dict(sorted(python.items())),
        "actions": dict(sorted(actions.items())),
    }


def _workflow_files(root: Path) -> list[Path]:
    github = root / ".github"
    return sorted(
        path
        for pattern in ("workflows/*.yml", "workflows/*.yaml", "actions/*/action.yml", "actions/*/action.yaml")
        for path in github.glob(pattern)
    )


def apply(root: Path, lock: dict) -> None:
    """Write the lock and move Python pins and action commits to it."""
    (root / LOCK).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    for project, names in PYTHON.items():
        path = root / project
        text = path.read_text()
        for name in names:
            text = re.sub(rf'"{re.escape(name)}==[^"]+"', f'"{name}=={lock["python"][name]}"', text)
        path.write_text(text)
    for workflow in _workflow_files(root):
        text = workflow.read_text()

        def pin(match: re.Match) -> str:
            repository = match.group(2)
            action = lock["actions"].get(repository)
            if not action:
                return match.group(0)
            return f"{match.group(1)}{repository}{match.group(3)}@{action['commit']} # v{action['version']}"

        workflow.write_text(USES.sub(pin, text))


def check(root: Path, registry: Path | None = None) -> list[str]:
    """Return every version that lives outside the lock, or a lock that left the registry."""
    problems = []
    path = root / LOCK
    if not path.is_file():
        return [f"{LOCK} is missing"]
    lock = json.loads(path.read_text())
    script = (root / SCRIPT).read_text()
    for name, (kind, _template) in TOOLS.items():
        entry = lock.get("tools", {}).get(name)
        if not entry or entry.get("kind") != kind or not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")):
            problems.append(f"lock entry for tool {name} is incomplete")
        if f"install_locked {name}" not in script:
            problems.append(f"{SCRIPT} does not install {name} from the lock")
    if re.search(r"https://(github\.com|codeload\.github\.com)/", script) or re.search(r"\b[0-9a-f]{64}\b", script):
        problems.append(f"{SCRIPT} writes a download or checksum by hand")
    for project, names in PYTHON.items():
        text = (root / project).read_text()
        for name in names:
            if f'"{name}=={lock.get("python", {}).get(name)}"' not in text:
                problems.append(f"{project} pins {name} outside the lock")
    for workflow in _workflow_files(root):
        for match in USES.finditer(workflow.read_text()):
            repository = match.group(2)
            if repository.startswith("NDDev-Technocracy-Standarts/"):
                continue
            action = lock.get("actions", {}).get(repository)
            if not action or match.group(4) != action.get("commit"):
                problems.append(f"{workflow.relative_to(root)} pins {repository} outside the lock")
    if registry is not None:
        lines = registry_lines(registry)
        for name, entry in lock.get("tools", {}).items():
            if lines.get(name, {}).get("version") != entry.get("version"):
                problems.append(f"tool {name} differs from the registry")
        for name, version in lock.get("python", {}).items():
            if lines.get(name, {}).get("version") != version:
                problems.append(f"Python tool {name} differs from the registry")
        for name, action in lock.get("actions", {}).items():
            if lines.get(name, {}).get("commit") != action.get("commit"):
                problems.append(f"action {name} differs from the registry")
    return problems
