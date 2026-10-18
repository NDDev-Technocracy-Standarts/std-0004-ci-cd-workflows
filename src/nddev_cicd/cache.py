"""Owned bounded local cache namespaces with native process locking."""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import time
from pathlib import Path

from .model import Invalid, atomic_json, identity


@contextlib.contextmanager
def lock(path: Path, *, blocking: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            if not path.stat().st_size:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_UN)


@contextlib.contextmanager
def namespace(root: Path, inputs: dict):
    if root.is_symlink():
        raise Invalid("A cache owner root cannot be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    owner = root / ".nddev-cache-owner.json"
    with lock(root / ".owner.lock"):
        if owner.exists() and json.loads(owner.read_text()) != {"schema": 1, "owner": "nddev-cicd"}:
            raise Invalid("Cache root belongs to another owner")
        if not owner.exists() and any(p.name != ".owner.lock" for p in root.iterdir()):
            raise Invalid("Do not adopt an existing unowned cache directory")
        atomic_json(owner, {"schema": 1, "owner": "nddev-cicd"})
    name = identity(inputs)
    path = root / name
    with lock(root / f"{name}.lock"):
        if path.is_symlink():
            raise Invalid("Cache namespace cannot be a symlink")
        path.mkdir(exist_ok=True)
        atomic_json(path / "identity.json", inputs)
        os.utime(path, None)
        yield path


def size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())


def reclaim(root: Path, budget: int, min_free: int, ttl_seconds: int) -> list[str]:
    if budget <= 0 or min_free < 0 or ttl_seconds < 1:
        raise Invalid("Explicit positive cache budget/TTL and available-disk reserve are required")
    owner = root / ".nddev-cache-owner.json"
    if (
        root.is_symlink()
        or not owner.exists()
        or json.loads(owner.read_text()) != {"schema": 1, "owner": "nddev-cicd"}
    ):
        raise Invalid("No matching cache owner; nothing reclaimed")
    removed = []
    candidates = sorted(
        (
            p
            for p in root.iterdir()
            if p.is_dir() and not p.is_symlink() and re.fullmatch(r"[0-9a-f]{64}", p.name)
        ),
        key=lambda p: p.stat().st_mtime,
    )
    total = sum(size(p) for p in candidates)
    for path in candidates:
        if path.is_symlink() or not (path / "identity.json").is_file():
            continue
        expired = time.time() - path.stat().st_mtime > ttl_seconds
        pressure = total > budget or shutil.disk_usage(root).free < min_free
        if not expired and not pressure:
            continue
        try:
            with lock(root / f"{path.name}.lock", blocking=False):
                amount = size(path)
                shutil.rmtree(path)  # only this producer's inactive identity namespace, never host-wide state
                total -= amount
                removed.append(path.name)
        except (BlockingIOError, OSError):
            continue
    return removed
