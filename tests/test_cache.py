"""Cache ownership/admission rejects mistakes before touching another producer's files."""

import pytest

from nddev_cicd import cache
from nddev_cicd.model import Invalid


@pytest.mark.parametrize("existing_lock", [False, True])
def test_foreign_cache_is_rejected_without_even_a_new_lock_file(tmp_path, existing_lock):
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "user-data").write_text("preserved")
    if existing_lock:
        (foreign / ".owner.lock").touch()
    before = {p.name: p.read_bytes() for p in foreign.iterdir()}
    with pytest.raises(Invalid, match="unowned"), cache.namespace(foreign, {"fixture": True}):
        raise AssertionError("An unowned cache was entered")
    assert {p.name: p.read_bytes() for p in foreign.iterdir()} == before


def test_parallel_initialization_waits_for_the_owner_marker_publication(tmp_path, monkeypatch):
    import contextlib
    import os
    import threading
    from concurrent.futures import ThreadPoolExecutor

    root = tmp_path / "owned"
    root.mkdir()
    owner = root / ".nddev-cache-owner.json"
    waiting = threading.Event()
    native_lock = cache.lock

    @contextlib.contextmanager
    def observe_lock(path, *, blocking=True):
        if path == root / ".owner.lock":
            waiting.set()
        with native_lock(path, blocking=blocking):
            yield

    def concurrent_namespace():
        with cache.namespace(root, {"fixture": True}, blocking=False) as selected:
            return selected

    monkeypatch.setattr(cache, "lock", observe_lock)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with native_lock(root / ".owner.lock"):
            # Pause the native atomic writer between temporary creation and rename.
            owner.with_name(owner.name + f".tmp-{os.getpid()}").write_text("{")
            contender = pool.submit(concurrent_namespace)
            try:
                assert waiting.wait(2), "Parallel initialization rejected the in-flight owner marker"
                assert not contender.done()
            finally:
                cache.atomic_json(owner, {"schema": 1, "owner": "nddev-cicd"})
        assert contender.result(timeout=2).is_dir()


@pytest.mark.parametrize("bad", [None, True, -1, "1024"])
def test_compiler_cache_budget_is_explicit_and_valid_before_admission(tmp_path, bad):
    with (
        pytest.raises(Invalid),
        cache.compiler(
            tmp_path,
            {"cache_budget_bytes": bad, "cache_min_free_bytes": 0, "cache_ttl_seconds": 60},
            {},
            "contract.toml",
        ),
    ):
        raise AssertionError("Invalid compiler cache was admitted")
    assert not list(tmp_path.iterdir())


def test_cargo_and_compiler_roots_cannot_compete_for_one_retention_budget(tmp_path, monkeypatch):
    root = tmp_path / "shared"
    monkeypatch.setenv("NDDEV_CACHE_ROOT", str(root))
    monkeypatch.setenv("NDDEV_CCACHE_ROOT", str(root))
    policy = {"cache_budget_bytes": 1024**2, "cache_min_free_bytes": 0, "cache_ttl_seconds": 60}
    with pytest.raises(Invalid, match="separate"), cache.compiler(tmp_path, policy, {}, "contract.toml"):
        raise AssertionError("Conflicting cache owners were admitted")
    assert not root.exists()


def test_busy_namespace_does_not_wait_or_modify_active_files(tmp_path):
    with cache.namespace(tmp_path / "owned", {"repository": "fixture"}) as owned:
        (owned / "active").write_text("keep")
        with (
            pytest.raises(BlockingIOError),
            cache.namespace(tmp_path / "owned", {"repository": "fixture"}, blocking=False),
        ):
            raise AssertionError("An active namespace was entered")
        assert (owned / "active").read_text() == "keep"


def test_rust_cache_uses_contract_environment_and_records_reuse(tmp_path, monkeypatch):
    from nddev_cicd import ci

    (tmp_path / "contract.toml").write_text("schema = 1")
    contract = {
        "profiles": ["rust"],
        "_path": "contract.toml",
        "environment": {"NDDEV_CACHE_ROOT": str(tmp_path / "owned")},
        "rust": {
            "cache_budget_bytes": 1024**2,
            "cache_min_free_bytes": 0,
            "cache_ttl_seconds": 60,
        },
    }
    monkeypatch.delenv("NDDEV_CACHE_ROOT", raising=False)
    monkeypatch.setattr(ci.subprocess, "check_output", lambda *a, **k: "rustc fixture")
    directories = []

    def execute(root, selected, output):
        from pathlib import Path

        target = Path(selected["environment"]["CARGO_TARGET_DIR"])
        directories.append(target)
        target.mkdir(exist_ok=True)
        return {"status": "success"}

    monkeypatch.setattr(ci, "_execute", execute)
    ci._execute_with_rust_cache(tmp_path, contract, tmp_path / "first")
    ci._execute_with_rust_cache(tmp_path, contract, tmp_path / "second")
    import json

    assert directories[0] == directories[1]
    assert not json.loads((tmp_path / "first/cache.json").read_text())["target_present"]
    assert json.loads((tmp_path / "second/cache.json").read_text())["target_present"]
