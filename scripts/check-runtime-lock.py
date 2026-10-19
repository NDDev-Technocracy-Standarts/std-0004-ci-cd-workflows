"""Bind authored workflow pins to exact immutable implementation/facade Git sources."""

import json
import re
import subprocess
import tomllib
from pathlib import Path

lock = json.loads(Path(".github/runtime-lock.json").read_text())
repository, implementation, facade = (lock[key] for key in ("repository", "implementation", "facade"))
for ref in (implementation, facade):
    assert re.fullmatch("[0-9a-f]{40}", ref)
    subprocess.run(["git", "merge-base", "--is-ancestor", ref, "HEAD"], check=True)
package = tomllib.loads(
    subprocess.check_output(["git", "show", implementation + ":pyproject.toml"], text=True)
)
assert package["project"]["version"] == lock["package"]
pattern = re.compile(re.escape(repository) + r"/(\.github/(?:actions|workflows)/[^\s@]+)@([0-9a-f]{40})")
for path in Path(".github/workflows").glob("*.yml"):
    for relative, ref in pattern.findall(path.read_text()):
        assert ref == (facade if relative.startswith(".github/workflows/") else implementation), path
for name in ("source.yml", "release.yml", "public-security.yml"):
    source = subprocess.check_output(["git", "show", f"{facade}:.github/workflows/{name}"], text=True)
    assert implementation in source
    assert all(ref == implementation for _, ref in pattern.findall(source))
print("Native package identity and source/delivery/facade bindings agree")
