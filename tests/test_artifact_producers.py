"""A retained source is the same native execution, not an arbitrary older successful artifact."""

import copy
import hashlib
import io
import json
import zipfile

import pytest

from nddev_cicd import github
from nddev_cicd.model import Invalid

REPOSITORY, REVISION = "example/project", "a" * 40


@pytest.fixture
def producer(monkeypatch):
    run = {
        "run_attempt": 2,
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "head_sha": REVISION,
        "status": "in_progress",
    }
    source = {
        "repository": REPOSITORY,
        "run_id": "7",
        "attempt": "1",
        "check_run_id": "11",
        "tested_revision": REVISION,
    }
    built = {
        "id": 11,
        "check_run_url": f"https://api.github.com/repos/{REPOSITORY}/check-runs/11",
        "run_id": 7,
        "run_attempt": 1,
        "name": "native source",
        "head_sha": REVISION,
        "status": "completed",
        "conclusion": "success",
        "runner_id": 8,
        "runner_name": "jit-one-job",
        "started_at": "2026-01-01T01:00:00Z",
        "completed_at": "2026-01-01T01:01:00Z",
        "steps": [{"name": "native checks", "conclusion": "success", "number": 1}],
    }
    clone = copy.deepcopy(built) | {
        "id": 22,
        "run_attempt": 2,
        "check_run_url": f"https://api.github.com/repos/{REPOSITORY}/check-runs/22",
    }
    original, latest = [built], [clone]

    def get(path):
        if "/attempts/1/jobs?" in path:
            return {"jobs": original}
        if "/jobs?filter=latest" in path:
            return {"jobs": latest}
        if path == f"repos/{REPOSITORY}/actions/runs/7":
            return run
        raise AssertionError(path)

    monkeypatch.setattr(github, "get", get)
    return run, source, original, latest


def test_native_rerun_clone_retains_execution_with_new_job_check_and_attempt(producer):
    _, source, _, _ = producer
    proof = github.producer(REPOSITORY, 7, REVISION, source)
    assert proof == {
        "producer_attempt": "1",
        "validation_attempt": "2",
        "check_run_id": "11",
        "latest_job_id": "22",
    }
    # An in-progress caller may check provenance; this alone never admits delivery.


@pytest.mark.parametrize(
    "field,value",
    [
        ("started_at", "2026-01-01T02:00:00Z"),
        ("completed_at", "2026-01-01T02:01:00Z"),
        ("runner_id", 99),
        ("runner_name", "a-new-runner"),
        ("name", "another source"),
        ("steps", [{"name": "different execution"}]),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("head_sha", "b" * 40),
        ("run_attempt", 1),
    ],
)
def test_rerun_or_changed_execution_cannot_reuse_an_old_payload(producer, field, value):
    _, source, _, latest = producer
    latest[0][field] = value
    with pytest.raises(Invalid, match="replaced|absent"):
        github.producer(REPOSITORY, 7, REVISION, source)


def test_failed_original_and_ambiguous_latest_execution_are_refused(producer):
    _, source, original, latest = producer
    original[0]["conclusion"] = "failure"
    with pytest.raises(Invalid, match="not successful"):
        github.producer(REPOSITORY, 7, REVISION, source)
    original[0]["conclusion"] = "success"
    latest.append(copy.deepcopy(latest[0]))
    with pytest.raises(Invalid, match="replaced|absent"):
        github.producer(REPOSITORY, 7, REVISION, source)


@pytest.mark.parametrize(
    "field,value",
    [
        ("check_run_id", "22"),
        ("check_run_id", "unknown"),
        ("attempt", "3"),
        ("repository", "foreign/project"),
        ("tested_revision", "b" * 40),
    ],
)
def test_producer_identity_cannot_move_between_attempts_or_repositories(producer, field, value):
    _, source, _, _ = producer
    with pytest.raises(Invalid):
        github.producer(REPOSITORY, 7, REVISION, source | {field: value})


def test_bundle_downloads_one_digest_bound_candidate_and_requires_retained_proof(tmp_path, monkeypatch):
    source = {
        "attempt": "1",
        "check_run_id": "11",
        "library_repository": "example/library",
        "library_ref": "c" * 40,
    }
    result = {
        "status": "success",
        "expected": ["native"],
        "results": [{"name": "native", "status": "success"}],
        "identity": source,
    }
    manifest = {"source": source}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("result.json", json.dumps(result))
        archive.writestr("artifact.tar.gz", b"native payload")
        archive.writestr("artifact.tar.gz.json", json.dumps(manifest))
    blob = buffer.getvalue()
    selected = {
        "id": 17,
        "name": "nddev-source-7-1-primary",
        "expired": False,
        "digest": "sha256:" + hashlib.sha256(blob).hexdigest(),
    }
    monkeypatch.setattr(github, "get", lambda _: {"artifacts": [selected]})
    calls = []

    def admitted(_repo, _run, _revision, _workflow, observed=None):
        calls.append(observed)
        if observed is not None:
            assert observed == source
        return {"attempt": "2"}

    monkeypatch.setattr(github, "eligible", admitted)
    monkeypatch.setattr(
        github, "download", lambda _repo, ident, output: output.write_bytes(blob) if ident == 17 else None
    )
    monkeypatch.setenv("NDDEV_LIBRARY_REPOSITORY", source["library_repository"])
    monkeypatch.setenv("NDDEV_LIBRARY_REF", source["library_ref"])
    archive, _, observed = github.bundle(
        REPOSITORY, 7, REVISION, ".github/workflows/ci.yml", tmp_path / "bound"
    )
    assert archive.read_bytes() == b"native payload" and observed == source
    assert calls == [None, source]
    selected["digest"] = "sha256:" + "0" * 64
    with pytest.raises(Invalid, match="archive digest"):
        github.bundle(REPOSITORY, 7, REVISION, ".github/workflows/ci.yml", tmp_path / "corrupt")
