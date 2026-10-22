"""Select an exact native Rust toolchain without refreshing installed SDKs."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .model import Invalid, Unavailable
from .process import run


def native(arguments: list[str], *, timeout: int = 30) -> str:
    with tempfile.TemporaryDirectory(prefix="nddev-rust-setup-") as directory:
        output, errors = (Path(directory) / name for name in ("stdout", "stderr"))
        command = ["rustup", *arguments]
        result = run(
            command,
            Path.cwd(),
            output,
            timeout=timeout,
            env={"RUSTUP_AUTO_INSTALL": "0"},
            stderr_log=errors,
        )
        if result["detail"] == "cancelled":
            raise KeyboardInterrupt
        if result["detail"] == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        if result["status"] != "success":
            raise subprocess.CalledProcessError(
                result["exit_code"] or 127, command, stderr=errors.read_text(errors="replace")[-16384:]
            )
        return output.read_text().strip()


def install(arguments: list[str]) -> None:
    for attempt in range(2):
        try:
            native(arguments, timeout=600)
            return
        except subprocess.TimeoutExpired:
            transient = True
        except subprocess.CalledProcessError as error:
            transient = any(
                word in (error.stderr or "").lower()
                for word in (
                    "timed out",
                    "connection reset",
                    "could not resolve host",
                    "failed to connect",
                    "error sending request",
                    "http request returned an unsuccessful status code: 5",
                )
            )
            if not transient:
                raise Invalid(
                    "Native Rust installation failed; the exact requested SDK was not selected"
                ) from error
        if attempt == 1:
            raise Unavailable("infrastructure.external-download: native Rust installation did not complete")


def prepare(toolchain: str, components: list[str], targets: list[str], *, allow_install: bool = True) -> dict:
    exact = re.fullmatch(
        r"(1\.[0-9]+\.[0-9]+|nightly-[0-9]{4}-[0-9]{2}-[0-9]{2})(?:-[A-Za-z0-9_-]+)?", toolchain
    )
    if not exact or any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", item) for item in components + targets
    ):
        raise Invalid(
            "Rust setup requires an exact release or dated nightly and native component/target names"
        )
    rustup = shutil.which("rustup")
    if rustup is None:
        raise Invalid("Native rustup is required; provision its verified distribution before setup")
    proxy = Path(rustup).absolute().parent
    if any(character in str(proxy) for character in "\r\n"):
        raise Invalid("Rust proxy directory cannot contain native file-command separators")
    if not all((proxy / name).is_file() for name in ("rustc", "cargo")):
        raise Invalid("Native rustup requires its sibling rustc/cargo proxies")
    reused = True
    try:
        compiler = native(["run", toolchain, "rustc", "-vV"])
    except subprocess.CalledProcessError as error:
        if "is not installed" not in (error.stderr or ""):
            raise Invalid("The selected native Rust compiler did not run") from error
        if not allow_install:
            raise Unavailable(
                "The exact requested Rust toolchain is not installed; installation is disabled"
            ) from error
        install(["toolchain", "install", toolchain, "--profile", "minimal", "--no-self-update"])
        compiler = native(["run", toolchain, "rustc", "-vV"])
        reused = False
    facts = dict(line.split(": ", 1) for line in compiler.splitlines() if ": " in line)
    if not all(facts.get(key) for key in ("host", "release")) or (
        exact[1].startswith("1.") and facts.get("release") != exact[1]
    ):
        raise Invalid("Native rustc identity differs from the exact requested toolchain")
    host = facts["host"]
    installed_components = set(
        native(["component", "list", "--installed", "--toolchain", toolchain]).splitlines()
    )
    installed_targets = set(native(["target", "list", "--installed", "--toolchain", toolchain]).splitlines())
    missing_components = [
        item
        for item in components
        if item not in installed_components and f"{item}-{host}" not in installed_components
    ]
    missing_targets = [item for item in targets if item not in installed_targets]
    if (missing_components or missing_targets) and not allow_install:
        raise Unavailable("Requested native Rust components or targets are absent; installation is disabled")
    for kind, missing in (("component", missing_components), ("target", missing_targets)):
        if missing:
            install([kind, "add", "--toolchain", toolchain, *missing])
            actual = set(native([kind, "list", "--installed", "--toolchain", toolchain]).splitlines())
            if any(item not in actual and f"{item}-{host}" not in actual for item in missing):
                raise Invalid("Native Rust installation did not provide every requested component/target")
            reused = False
    return {
        "toolchain": toolchain,
        "release": facts["release"],
        "host": host,
        "reused": reused,
        "proxy_directory": str(proxy),
        "components": components,
        "targets": targets,
    }


def export(result: dict) -> None:
    """Native file commands affect following steps, without changing a shared default."""
    if os.environ.get("GITHUB_ENV"):
        with Path(os.environ["GITHUB_ENV"]).open("a") as stream:
            stream.write(f"RUSTUP_TOOLCHAIN={result['toolchain']}\nRUSTUP_AUTO_INSTALL=0\n")
    if os.environ.get("GITHUB_PATH"):
        with Path(os.environ["GITHUB_PATH"]).open("a") as stream:
            stream.write(result["proxy_directory"] + "\n")
