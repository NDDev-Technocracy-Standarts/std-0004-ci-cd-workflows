"""Native input transport retries must never retry or waive audit findings."""

import subprocess
from pathlib import Path

import pytest

from nddev_cicd import rustsec
from nddev_cicd.model import Invalid, Unavailable


def test_real_shallow_git_reuses_objects_and_advances_to_current_source(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    rustsec.git(upstream, "init", "--quiet")
    for key, value in (("user.name", "Synthetic Fixture"), ("user.email", "fixture@example.invalid")):
        rustsec.git(upstream, "config", key, value)
    (upstream / "advisory.txt").write_text("first fixture")
    rustsec.git(upstream, "add", ".")
    rustsec.git(upstream, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture")
    monkeypatch.setattr(rustsec, "SOURCE", upstream.as_uri())
    commands, native = [], subprocess.run

    def invoke(command, **kwargs):
        if command[:2] == ["cargo", "audit"]:
            commands.append(command)
            database = Path(command[command.index("--db") + 1])
            assert (database / "advisory.txt").read_text() == (upstream / "advisory.txt").read_text()
            return subprocess.CompletedProcess(command, 0)
        return native(command, **kwargs)

    monkeypatch.setattr(rustsec.subprocess, "run", invoke)
    storage = tmp_path / "owned"
    for _ in range(2):
        assert rustsec.audit(tmp_path, storage, reserve=0) == 0
    database = next(storage.glob("*/repository"))
    assert rustsec.git(database, "rev-parse", "--is-shallow-repository") == "true"
    before = (database / ".git/objects").stat().st_ino
    (upstream / "advisory.txt").write_text("updated fixture")
    rustsec.git(upstream, "add", ".")
    rustsec.git(upstream, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "updated")
    assert rustsec.audit(tmp_path, storage, reserve=0) == 0
    assert (database / ".git/objects").stat().st_ino == before
    assert len(commands) == 3
    assert all(command[-3:] == ["--no-fetch", "--deny", "warnings"] for command in commands)


@pytest.mark.parametrize("failure", ["timed out", "early EOF", "authentication failed"])
def test_fetch_is_bounded_and_only_retries_transport(failure, monkeypatch, tmp_path):
    calls = []

    def fail(*args):
        calls.append(args)
        raise subprocess.CalledProcessError(128, "git", stderr=failure)

    monkeypatch.setattr(rustsec, "git", fail)
    with pytest.raises(Unavailable, match="infrastructure.external-download"):
        rustsec.fetch(tmp_path)
    assert len(calls) == (1 if failure == "authentication failed" else 2)


def test_audit_verdict_is_not_retried_or_changed(tmp_path, monkeypatch):
    calls = []
    native = subprocess.run

    def invoke(command, **kwargs):
        if command[:2] == ["cargo", "audit"]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 17)
        return native(command, **kwargs)

    monkeypatch.setattr(rustsec.subprocess, "run", invoke)
    monkeypatch.setattr(rustsec, "fetch", lambda repo: None)
    original = rustsec.git

    def fixture(repo, *args):
        if args[0] == "checkout":
            return ""
        if args == ("rev-parse", "HEAD"):
            return "a" * 40
        return original(repo, *args)

    monkeypatch.setattr(rustsec, "git", fixture)
    assert rustsec.audit(tmp_path, tmp_path / "cache", reserve=0) == 17
    assert len(calls) == 1


def test_unowned_and_redirected_cache_paths_are_refused(tmp_path):
    owned = tmp_path / "cache"
    owned.mkdir()
    (owned / "foreign").write_text("preserve")
    with pytest.raises(Invalid, match="unowned"):
        rustsec.audit(tmp_path, owned, reserve=0)
    link = tmp_path / "redirected"
    link.symlink_to(owned, target_is_directory=True)
    with pytest.raises(Invalid, match="symlink"):
        rustsec.audit(tmp_path, link, reserve=0)
    assert (owned / "foreign").read_text() == "preserve"


def test_failed_refresh_never_invokes_the_scanner(tmp_path, monkeypatch):
    called = []
    native = subprocess.run

    def invoke(command, **kwargs):
        if command[:2] == ["cargo", "audit"]:
            called.append(command)
        return native(command, **kwargs)

    def unavailable(_repository):
        raise Unavailable("infrastructure.external-download: fixture")

    monkeypatch.setattr(rustsec.subprocess, "run", invoke)
    monkeypatch.setattr(rustsec, "fetch", unavailable)
    with pytest.raises(Unavailable, match="external-download"):
        rustsec.audit(tmp_path, tmp_path / "cache", reserve=0)
    assert not called
