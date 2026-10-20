"""Exercise the real curl retry boundary over an owned HTTPS fixture."""

import hashlib
import http.server
import io
import os
import platform
import shutil
import ssl
import subprocess
import tarfile
import threading
import time
from pathlib import Path

import pytest


@pytest.mark.skipif(
    platform.system() != "Linux" or not shutil.which("openssl"), reason="Native Linux bootstrap"
)
@pytest.mark.parametrize("installer", ["file", "archive", "uv"])
@pytest.mark.parametrize("corrupt", [False, True])
@pytest.mark.parametrize("failure_mode", ["status", "timeout"])
def test_bootstrap_retries_transport_but_never_integrity(tmp_path, installer, corrupt, failure_mode):
    certificate, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        check=True,
        capture_output=True,
    )
    binary = b"#!/usr/bin/env bash\nprintf 'native fixture\\n'\n"
    payload = binary
    if installer in {"archive", "uv"}:
        content = io.BytesIO()
        with tarfile.open(fileobj=content, mode="w:gz") as archive:
            member = tarfile.TarInfo("uv-x86_64-unknown-linux-gnu/uv" if installer == "uv" else "fixture")
            member.size = len(binary)
            archive.addfile(member, io.BytesIO(binary))
        payload = content.getvalue()
    checksum = "0" * 64 if corrupt else hashlib.sha256(payload).hexdigest()
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if len(requests) == 1 and failure_mode == "timeout":
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload[:1])
                self.wfile.flush()
                time.sleep(2)
                return
            self.send_response(503 if len(requests) == 1 else 200)
            self.send_header("Content-Length", str(0 if len(requests) == 1 else len(payload)))
            self.end_headers()
            if len(requests) > 1:
                self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("localhost", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"https://localhost:{server.server_port}/fixture"
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if installer == "uv":
        source = (scripts / "library-uv.sh").read_text()
        source = source.replace(
            "https://github.com/astral-sh/uv/releases/download/0.13.1/uv-$target.$extension", url
        ).replace("eadd9d27c134ab5ac1ffd4473b97a741407f3ea238288f03121fc4deddf90220", checksum)
    else:
        source = (scripts / "prepare-linux-tools.sh").read_text().split("capabilities=", 1)[0]
        source += f"install_{installer} '{url}' '{checksum}' fixture\n"
    # Preserve the production retry/per-attempt ratio while exercising a real timeout quickly.
    source = source.replace("--max-time 120", "--max-time 1")
    source = source.replace("--retry-max-time 120", "--retry-max-time 1")
    source = source.replace("--retry-max-time 480", "--retry-max-time 4")
    script = tmp_path / "bootstrap.sh"
    script.write_text(source)
    env = dict(os.environ, RUNNER_TEMP=str(tmp_path), CURL_CA_BUNDLE=str(certificate))
    try:
        result = subprocess.run(
            ["bash", str(script)], env=env, capture_output=True, text=True, timeout=30, check=False
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert len(requests) == 2
    assert (result.returncode != 0) is corrupt, result.stdout + result.stderr
    if installer == "uv" and not corrupt:
        # The successful installer deliberately hands its job-owned directory to the caller.
        shutil.rmtree(Path(result.stdout.strip()).parent)
    elif installer != "uv":
        assert (tmp_path / "nddev-native-tools/fixture").exists() is not corrupt
