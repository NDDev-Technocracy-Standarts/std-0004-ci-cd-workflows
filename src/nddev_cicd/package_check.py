"""Exercise a built Python distribution outside its source tree with locked runtime dependencies."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from .model import Invalid


def check(root: Path) -> None:
    config = tomllib.loads((root / "pyproject.toml").read_text())
    wheels = list((root / "dist").glob("*.whl"))
    sdists = list((root / "dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise Invalid("Build exactly one wheel and sdist into a clean owned package output")
    with zipfile.ZipFile(wheels[0]) as wheel:
        if not any(name.endswith("/METADATA") for name in wheel.namelist()):
            raise Invalid("Wheel metadata is absent")
    modules = sorted(
        path.name for path in (root / "src").iterdir() if path.is_dir() and (path / "__init__.py").exists()
    )
    if not modules:
        raise Invalid("Declare a Python src package before consumer import")
    with tempfile.TemporaryDirectory(prefix="nddev-wheel-consumer-") as directory:
        workspace = Path(directory)
        environment = workspace / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(environment)], check=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        requirements = workspace / "requirements.txt"
        with requirements.open("w") as stream:
            subprocess.run(
                ["uv", "export", "--locked", "--no-dev", "--no-emit-project"],
                cwd=root,
                stdout=stream,
                check=True,
            )
        subprocess.run(["uv", "pip", "sync", "--python", str(python), str(requirements)], check=True)
        subprocess.run(
            ["uv", "pip", "install", "--no-deps", "--python", str(python), str(wheels[0])], check=True
        )
        expression = "import importlib; " + "; ".join(
            f"importlib.import_module({name!r})" for name in modules
        )
        subprocess.run([str(python), "-I", "-c", expression], cwd=workspace, check=True)
    if not config.get("project", {}).get("name"):
        raise Invalid("Package identity is absent")


if __name__ == "__main__":
    check(Path.cwd())
