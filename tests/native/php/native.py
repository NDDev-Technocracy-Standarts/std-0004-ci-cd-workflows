"""Invoke the pinned native PHP/Composer SDK in a Linux container with caller ownership."""

import os
import subprocess
import sys
from pathlib import Path

image = "composer@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac"
subprocess.run(
    [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--env",
        "COMPOSER_HOME=/tmp/composer",
        "--volume",
        f"{Path.cwd()}:/work",
        "--workdir",
        "/work",
        image,
        *sys.argv[1:],
    ],
    check=True,
)
