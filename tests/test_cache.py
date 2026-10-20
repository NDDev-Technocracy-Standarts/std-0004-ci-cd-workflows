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
