"""Cache ownership/admission rejects mistakes before touching another producer's files."""

import pytest

from nddev_cicd import cache
from nddev_cicd.model import Invalid


def test_foreign_cache_is_rejected_without_even_a_new_lock_file(tmp_path):
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "user-data").write_text("preserved")
    with pytest.raises(Invalid, match="unowned"), cache.namespace(foreign, {"fixture": True}):
        raise AssertionError("An unowned cache was entered")
    assert [p.name for p in foreign.iterdir()] == ["user-data"]


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
