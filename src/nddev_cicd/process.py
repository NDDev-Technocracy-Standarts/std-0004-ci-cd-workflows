"""Run intentional trusted native commands with bounded failure-preserving execution."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from .model import Invalid


def run(
    command: list[str] | str, root: Path, log: Path, *, timeout: int = 900, env: dict[str, str] | None = None
) -> dict:
    if not command or not isinstance(timeout, int) or timeout < 1 or timeout > 7200:
        raise Invalid("Native command and bounded timeout (1..7200 seconds) are required")
    if isinstance(command, str):
        # Only explicitly trusted project commands use a shell. All other inputs are data.
        command = (
            [
                "pwsh",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$ErrorActionPreference='Stop'; " + command + "; if ($LASTEXITCODE) { exit $LASTEXITCODE }",
            ]
            if os.name == "nt"
            else ["bash", "--noprofile", "--norc", "-euo", "pipefail", "-c", command]
        )
    if not all(isinstance(word, str) and "\0" not in word for word in command):
        raise Invalid("Command must contain valid argument strings")
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    status, code, detail = "failure", None, ""
    with log.open("w", encoding="utf-8") as stream:
        try:
            child_environment = {
                k: v
                for k, v in os.environ.items()
                if k not in {"UV_PROJECT_ENVIRONMENT", "UV_PROJECT", "VIRTUAL_ENV", "PYTHONPATH"}
            }
            child = subprocess.Popen(
                command,
                cwd=root,
                env={**child_environment, **(env or {})},
                stdout=stream,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=os.name != "nt",
            )
            try:
                code = child.wait(timeout=timeout)
                status = "success" if code == 0 else "failure"
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                detail = "cancelled" if isinstance(error, KeyboardInterrupt) else "timeout"
                if os.name != "nt":
                    os.killpg(child.pid, signal.SIGTERM)
                else:
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        check=False,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                    )
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name != "nt":
                        os.killpg(child.pid, signal.SIGKILL)
                    else:
                        child.kill()
                    child.wait()
                code = child.returncode
        except FileNotFoundError as error:
            status, detail = "unavailable", f"Required executable is absent: {error.filename}"
            stream.write(detail + "\n")
    return {
        "status": status,
        "exit_code": code,
        "seconds": round(time.monotonic() - started, 4),
        "detail": detail,
        "log": str(log),
    }
