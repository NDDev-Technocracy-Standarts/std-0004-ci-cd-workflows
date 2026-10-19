"""Consumer regressions exercise real Git inputs, native processes and bounded API contracts."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from nddev_cicd import ci, config, documentation, feedback, impact, reports
from nddev_cicd.model import Invalid, git
from nddev_cicd.process import run

DOC_COMMANDS = """schema=1
profiles=["documentation"]
[commands.documentation]
external-links=["git","diff","--exit-code"]
generate=["git","diff","--exit-code"]
examples=["git","diff","--exit-code"]
"""


@pytest.mark.parametrize(
    "path,pattern,expected",
    [
        ("uv.lock", "**/*lock*", True),
        ("backend/Cargo.lock", "**/*lock*", True),
        ("a/b/c.py", "a/**", True),
        ("a/c.py", "a/**/c.py", True),
        ("a/b/c.py", "a/*.py", False),
        ("a/pyproject.toml", "pyproject.toml", False),
        ("pyproject.toml", "pyproject.toml", True),
    ],
)
def test_impact_globs_are_anchored_and_recursive(path, pattern, expected):
    assert impact.matches(path, pattern) is expected


def test_lock_change_selects_every_component_and_nested_scope_is_precise(repository):
    root = repository({"uv.lock": "a", "backend/deep/app.py": "a", "docs/index.md": "a"})
    base = git(root, "rev-parse", "HEAD")
    components = {"backend": {"paths": ["backend/**"]}, "docs": {"paths": ["docs/**"]}}
    (root / "backend/deep/app.py").write_text("b")
    git(root, "commit", "-am", "change nested source")
    assert impact.affected(root, base, "HEAD", components, ["**/*lock*"]) == ["backend"]
    base = git(root, "rev-parse", "HEAD")
    (root / "uv.lock").write_text("b")
    git(root, "commit", "-am", "change shared root lock")
    assert impact.affected(root, base, "HEAD", components, ["**/*lock*"]) == ["backend", "docs"]


def test_nested_lock_mutation_cannot_pass(repository, tmp_path):
    root = repository(
        {
            "README.md": "# Source\n",
            "admin/bun.lock": "original",
            "backend/Cargo.lock": "original",
            ".github/nddev-ci.toml": DOC_COMMANDS,
        }
    )
    contract = config.load(root)
    contract["commands"]["documentation"]["examples"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; Path('admin/bun.lock').write_text('changed')",
    ]
    result = ci.execute(root, contract, tmp_path / "out")
    assert set(result["identity"]["locks"]) == {"admin/bun.lock", "backend/Cargo.lock"}
    assert result["status"] == "failure"
    assert result["results"][-1]["changed_inputs"] == ["admin/bun.lock"]


def test_failed_native_diagnostics_are_bounded_redacted_and_visible(
    repository, tmp_path, monkeypatch, capsys
):
    root = repository({"README.md": "# Source\n", ".github/nddev-ci.toml": DOC_COMMANDS})
    monkeypatch.setenv("TEST_SECRET_TOKEN", "private-fixture-value")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    contract = config.load(root)
    contract["diagnostics"] = {"tail_lines": 2}
    contract["commands"]["documentation"]["examples"] = [
        sys.executable,
        "-c",
        "print('discarded'); print('assertion failed'); print('private-fixture-value'); raise SystemExit(1)",
    ]
    result = ci.execute(root, contract, tmp_path / "out")
    text = capsys.readouterr().out
    summary = (tmp_path / "summary.md").read_text()
    assert result["status"] == "failure" and "assertion failed" in text and "assertion failed" in summary
    assert "private-fixture-value" not in text + summary and "discarded" not in text
    assert "stop-commands" in text


def test_yaml_merge_override_is_valid_and_malformed_input_is_named(repository):
    root = repository(
        {"compose.yml": "base: &base\n  readonly: true\nweb:\n  <<: *base\n  readonly: false\n"}
    )
    assert documentation.check(root)["files"] == 1
    (root / "compose.yml").write_text("web:\n  port: 1\n  port: 2\n")
    with pytest.raises(Invalid, match="compose.yml"):
        documentation.check(root)
    (root / "compose.yml").write_text("web: [\n")
    with pytest.raises(Invalid, match="compose.yml"):
        documentation.check(root)


def test_bad_yaml_is_a_failed_stage_and_other_checks_still_run(repository, tmp_path):
    root = repository({"compose.yml": "web: [\n", ".github/nddev-ci.toml": DOC_COMMANDS})
    result = ci.execute(root, config.load(root), tmp_path / "out")
    assert result["failed"] == ["documentation.syntax"]
    assert result["results"][-2]["status"] == "success"


def test_output_directories_are_owned_per_invocation(repository, tmp_path):
    root = repository({"README.md": "# Source\n", ".github/nddev-ci.toml": DOC_COMMANDS})
    a = ci.execute(root, config.load(root), tmp_path / "a")
    b = ci.execute(root, config.load(root), tmp_path / "b")
    assert a["status"] == b["status"] == "success"
    with pytest.raises(FileExistsError):
        ci.execute(root, config.load(root), tmp_path / "a")


def test_not_applicable_is_explicit_and_cannot_waive_tests(repository, tmp_path):
    contract = """schema=1
profiles=["python"]
[not_applicable.python]
build="Application is deployed as source; no distribution is published"
consumer="Application has no wheel consumer; its entrypoint is tested directly"
[commands.python]
setup=["git","status","--porcelain"]
toolchain=["python3","--version"]
format=["python3","-m","compileall","-q","app.py"]
lint=["python3","-m","py_compile","app.py"]
type=["python3","-m","py_compile","app.py"]
test=["python3","-m","unittest","-v","test_app.py"]
[reports.python]
kind="unittest"
"""
    root = repository(
        {
            "requirements.txt": "# The fixture uses the caller-provided standard library.\n",
            "app.py": "def parse_port(value):\n    port = int(value)\n    if not 0 < port < 65536: raise ValueError('port')\n    return port\n",
            "test_app.py": "import unittest\nfrom app import parse_port\nclass Ports(unittest.TestCase):\n def test_parse(self): self.assertEqual(parse_port('8080'),8080)\n def test_reject(self):\n  with self.assertRaises(ValueError): parse_port('70000')\n",
            ".github/nddev-ci.toml": contract,
        }
    )
    result = ci.execute(root, config.load(root), tmp_path / "out")
    assert result["status"] == "success"
    assert [r["name"] for r in result["results"] if r["status"] == "not-applicable"] == [
        "python.build",
        "python.consumer",
    ]
    assert next(r for r in result["results"] if r["name"] == "python.test")["tests_executed"] == 2
    (root / ".github/nddev-ci.toml").write_text(contract.replace('build="Application', 'test="Application'))
    with pytest.raises(Invalid, match="cannot be waived"):
        config.load(root)
    assert reports.aggregate(["x"], [{"name": "x", "status": "not-applicable"}])["status"] == "failure"


@pytest.mark.parametrize(
    "manager,lock",
    [("npm", "package-lock.json"), ("bun", "bun.lock"), ("pnpm", "pnpm-lock.yaml"), ("yarn", "yarn.lock")],
)
def test_node_managers_follow_native_locks(repository, manager, lock):
    root = repository({"package.json": json.dumps({"packageManager": manager + "@1.2.3"}), lock: "{}"})
    definition = config.resolve(root, {}, ["typescript-javascript", "web"])
    for name in definition:
        if name not in {"typescript-javascript", "web"}:
            continue
        assert definition[name]["stages"]["setup"][0] == manager
        assert definition[name]["stages"]["test"][0] == manager
        assert definition[name]["locked_inputs"] == [lock]
    (root / "yarn.lock" if manager != "yarn" else root / "bun.lock").write_text("ambiguous")
    with pytest.raises(Invalid, match="unambiguous"):
        config.resolve(root, {}, ["web"])


@pytest.mark.parametrize(
    "name,manifest",
    [
        ("sql-data", "alembic.ini"),
        ("sql-data", "apps/api/migrations/versions/initial.py"),
        ("sql-data", "deploy/prod/sql/initial.sql"),
        ("container", "docker/web.Dockerfile"),
        ("container", "docker/Dockerfile.web"),
        ("container", "Containerfile"),
        ("shell-powershell", "deploy/prod/check.sh"),
    ],
)
def test_native_layouts_do_not_need_placeholder_manifests(repository, name, manifest):
    root = repository({manifest: "# native fixture\n"})
    assert name in config.resolve(root, {}, [name])


def test_cleanup_runs_after_native_failure_and_cannot_hide_it(repository, tmp_path):
    root = repository(
        {"Containerfile": "FROM scratch\n", ".github/nddev-ci.toml": 'schema=1\nprofiles=["container"]\n'}
    )
    contract = config.load(root)
    command = [sys.executable, "-c", "raise SystemExit(2)"]
    contract["commands"] = {
        "container": {stage: command for stage in ["lint", "build", "test", "scan", "sbom"]}
    }
    contract["commands"]["container"]["cleanup"] = [
        sys.executable,
        "-c",
        "from pathlib import Path; Path('cleaned').write_text('this run only')",
    ]
    result = ci.execute(root, contract, tmp_path / "out")
    assert result["status"] == "failure" and (root / "cleaned").read_text() == "this run only"
    assert next(r for r in result["results"] if r["name"] == "container.cleanup")["status"] == "success"


def test_git_config_injection_does_not_reach_native_children(repository, tmp_path, monkeypatch):
    root = repository({"file": "text"})
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "color.ui")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    result = run(["git", "config", "--get", "color.ui"], root, tmp_path / "config.log")
    assert result["status"] == "success" and Path(result["log"]).read_text().strip() == "false"


def test_shallow_history_and_zero_scanned_commits_fail(repository, tmp_path, monkeypatch):
    root = repository({"app.py": "x=1", ".github/nddev-ci.toml": 'schema=1\nprofiles=["security"]\n'})
    contract = config.load(root)
    defaults = config.catalog()
    defaults["security"]["stages"]["secrets"] = [
        sys.executable,
        "-c",
        "print('0 commits scanned. no leaks found')",
    ]
    monkeypatch.setattr(config, "catalog", lambda: defaults)
    contract["commands"] = {
        "security": {
            s: [sys.executable, "-c", "print('native override')"]
            for s in ["dependencies", "sast", "licenses"]
        }
    }
    result = ci.execute(root, contract, tmp_path / "zero")
    assert result["status"] == "failure" and "security.secrets" in result["failed"]
    clone = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--depth", "1", root.as_uri(), str(clone)], check=True, capture_output=True
    )
    result = ci.execute(clone, config.load(clone) | {"commands": contract["commands"]}, tmp_path / "depth")
    assert "fetch-depth: 0" in result["results"][0]["detail"]


def test_feedback_deduplicates_closed_markers_and_distinguishes_attempts(monkeypatch):
    run_data = {
        "id": 42,
        "run_attempt": 1,
        "repository": {"full_name": "example/project"},
        "path": ".github/workflows/ci.yml",
        "actor": {"login": "owner"},
        "status": "completed",
        "conclusion": "failure",
        "created_at": "2026-10-19T00:00:00Z",
    }
    issues, writes = [], []

    def get(path):
        if "/actions/runs/" in path:
            return run_data
        return issues

    def write(path, body):
        writes.append(body)
        issues.append(
            {
                "number": len(issues) + 1,
                "body": body["body"],
                "state": "closed",
                "user": {"login": "github-actions[bot]"},
            }
        )
        return {"html_url": "https://example.invalid/issue"}

    monkeypatch.setattr(feedback.github, "get", get)
    monkeypatch.setattr(feedback, "write", write)
    args = ("example/project", [".github/workflows/ci.yml"], ["owner"])
    assert feedback.publish(*args, run_id=42)["results"][0]["action"] == "published"
    assert feedback.publish(*args, run_id=42)["results"][0]["action"] == "existing"
    run_data["run_attempt"] = 2
    feedback.publish(*args, run_id=42)
    assert len(writes) == 2
    run_data["actor"] = {"login": "untrusted"}
    assert feedback.publish(*args, run_id=42)["results"] == []


def test_feedback_page_limit_fails_before_publication(monkeypatch):
    monkeypatch.setattr(feedback.github, "get", lambda path: [{}] * 100)
    with pytest.raises(Invalid, match="pagination budget"):
        feedback.pages("repos/example/project/issues", limit=2)
