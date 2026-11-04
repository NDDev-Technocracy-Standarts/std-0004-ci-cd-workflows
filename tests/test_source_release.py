from pathlib import Path

import yaml

ACTION = Path(__file__).resolve().parents[1] / ".github" / "actions" / "source-release" / "action.yml"


def _action():
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def test_inputs_cover_the_retired_reusable_contract():
    inputs = _action()["inputs"]
    assert inputs["version"]["required"] is True
    assert inputs["package-name"]["required"] is True
    for name in ("archive-paths", "runtime-paths", "notes-file", "github-token"):
        assert name in inputs
    assert "attest" not in inputs


def test_releases_carry_no_attestations():
    steps = _action()["runs"]["steps"]
    assert not [
        step for step in steps if "attest" in step.get("uses", "") or "Attest" in step.get("name", "")
    ]


def test_composite_steps_are_shell_explicit_and_pinned():
    for step in _action()["runs"]["steps"]:
        if "run" in step:
            assert step["shell"] == "bash"
        if "uses" in step:
            reference = step["uses"].split("@", 1)[1]
            assert len(reference) == 40 and all(c in "0123456789abcdef" for c in reference)


def test_release_is_created_once_with_a_verified_tag():
    runs = "\n".join(step.get("run", "") for step in _action()["runs"]["steps"])
    assert runs.count("release create") == 1
    assert "--verify-tag" in runs
    assert "--clobber" not in runs
    assert "ci-workflows" not in runs


def test_the_action_never_checks_out_code_itself():
    steps = _action()["runs"]["steps"]
    assert not any(str(step.get("uses", "")).startswith("actions/checkout@") for step in steps)
    assert any("refs/tags/${RELEASE_VERSION}^{commit}" in step.get("run", "") for step in steps)
