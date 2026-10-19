"""Native Buildx/OCI publication, TLS and immutable digest acceptance with an actual running image."""

import json
import shutil
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

import oci_fixture
import pytest

from nddev_cicd import oci
from nddev_cicd.model import Invalid, git


def test_native_oci_archive_publish_digest_and_invalid_build(repository, tmp_path):
    root = repository({"README.md": "# OCI fixture\n", ".gitignore": "dist/\n"})
    shutil.copyfile(Path(__file__).parent / "native/container/Dockerfile", root / "Dockerfile")
    git(root, "add", "Dockerfile")
    git(root, "commit", "-qm", "pinned native container input")
    revision = git(root, "rev-parse", "HEAD")
    (root / "index.html").write_text(revision)
    built = oci.build(root, "dist/image.oci.tar")
    archive = Path(built["archive"])
    record = json.loads(Path(built["metadata"]).read_text())
    fixture = oci_fixture.start(tmp_path / "registry")
    image = "nddev-oci-test:" + uuid.uuid4().hex
    container = None
    try:
        repo = fixture["endpoint"] + "/fixture"
        with pytest.raises(Invalid):
            oci.publish(archive, record, record["source"], repo)
        result = oci.publish(
            archive, record, record["source"], repo, certificates=Path(fixture["certificates"])
        )
        assert result["image"] == repo + "@" + record["digest"]
        repeated = oci.publish(
            archive, record, record["source"], repo, certificates=Path(fixture["certificates"])
        )
        assert repeated["digest"] == result["digest"]
        # The same checked OCI config/layers run; no source rebuild or host TLS exception is used.
        oci.skopeo(
            ["copy", "oci-archive:/input/image.oci.tar", "docker-daemon:" + image], archive, daemon=True
        )
        container = subprocess.check_output(
            ["docker", "run", "--detach", "--publish", "127.0.0.1::8080", image], text=True
        ).strip()
        ports = json.loads(
            subprocess.check_output(
                ["docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", container], text=True
            )
        )
        endpoint = "http://127.0.0.1:" + ports["8080/tcp"][0]["HostPort"]
        for _ in range(50):
            try:
                with urllib.request.urlopen(endpoint, timeout=2) as response:
                    assert response.read().decode() == revision
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("The actual OCI application did not serve its tested revision")
        corrupt = root / "dist/corrupt.oci.tar"
        corrupt.write_bytes(archive.read_bytes() + b"corrupt")
        with pytest.raises(Invalid, match="checked source metadata"):
            oci.publish(corrupt, record, record["source"], repo, certificates=Path(fixture["certificates"]))
        (root / "Dockerfile").write_text("FROM scratch\nRUN this-native-build-must-fail\n")
        with pytest.raises(Invalid, match="build failed"):
            oci.build(root, "dist/invalid.oci.tar")
    finally:
        if container:
            subprocess.run(["docker", "rm", "--force", container], check=False, capture_output=True)
        subprocess.run(["docker", "image", "rm", image], check=False, capture_output=True)
        oci_fixture.stop(tmp_path / "registry")
