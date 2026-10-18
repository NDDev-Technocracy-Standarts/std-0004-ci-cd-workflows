"""Generate the native profile reference from the runtime's single capability table."""

from pathlib import Path

from .config import catalog
from .model import Invalid, atomic_json, digest


def generate(root: Path, *, check: bool = False) -> None:
    lines = [
        "# Native profile reference",
        "",
        "Generated from the executed runtime catalog; not a native-fixture verification claim.",
        "",
        "| Profile | Required native stages | Project commands required |",
        "|---|---|---|",
    ]
    for name, definition in catalog().items():
        required = [stage for stage, command in definition["stages"].items() if command is None]
        lines.append(
            f"| `{name}` | {', '.join(definition['stages'])} | {', '.join(required) or 'Native defaults'} |"
        )
    lines += [
        "",
        "Commands can be overridden through the caller contract; selected baseline stages remain required.",
        "",
        "## Native defaults",
        "",
    ]
    import json

    lines += ["```json", json.dumps(catalog(), indent=2), "```", ""]
    text = "\n".join(lines)
    path = root / "docs/profiles.md"
    if check:
        if not path.exists() or path.read_text() != text:
            raise Invalid("Native profile reference drift: run python -m nddev_cicd reference")
    else:
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
        atomic_json(
            root / "generated/profiles-outputs.json",
            {
                "generator": "native-profile-reference",
                "inputs": {"src/nddev_cicd/profiles.json": digest(Path(__file__).with_name("profiles.json"))},
                "outputs": {"docs/profiles.md": {"sha256": digest(path), "state": "current"}},
            },
        )
