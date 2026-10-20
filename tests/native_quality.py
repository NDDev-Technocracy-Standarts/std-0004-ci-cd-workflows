"""Execute optional quality tools and reject controlled findings with their real native outputs."""

import json
import os
import sys

from nddev_cicd import ci, config


def test_actual_offline_semgrep_rejects_javascript_and_python_findings(repository, tmp_path, monkeypatch):
    executable = sys.executable.replace("\\", "/")
    root = repository(
        {
            "README.md": "# Native source-quality fixture\n",
            ".gitignore": ".nddev-reports/\n",
            "source.js": "const result = 'safe';\n",
            "source.py": "result = 'safe'\n",
            "rules.yml": "rules:\n- id: reject-python-eval\n  languages: [python]\n  pattern: eval($INPUT)\n  message: Do not execute input as code\n  severity: ERROR\n- id: reject-javascript-eval\n  languages: [javascript]\n  pattern: eval($INPUT)\n  message: Do not execute input as code\n  severity: ERROR\n",
            ".github/nddev-ci.toml": f'''schema=1
profiles=["documentation"]
[commands.documentation]
external-links=["{executable}","-c","print('native fixture')"]
generate=["{executable}","-c","print('native fixture')"]
examples=["{executable}","-c","print('native fixture')"]
[security]
engine="semgrep"
rules=["rules.yml"]
paths=["source.js","source.py"]
[extras.sast]
purpose="Exercise actual local Semgrep CE rules without an account or external rule service"
command=["@library","security-sast"]
timeout=120
''',
        }
    )
    # An inherited account must not participate in this explicitly offline OSS operation.
    monkeypatch.setenv("SEMGREP_APP_TOKEN", "not-a-real-account-token")
    positive = ci.execute(root, config.load(root), tmp_path / "positive")
    assert positive["status"] == "success"
    scanned = next(x for x in positive["results"] if x["name"] == "extra.sast")
    assert scanned["sast_targets"] == 2
    settings = (tmp_path / "positive/semgrep-settings.yml").read_text()
    assert "not-a-real-account-token" not in settings
    assert os.environ["SEMGREP_APP_TOKEN"] == "not-a-real-account-token"
    (root / "source.js").write_text("const result = eval(input);\n")
    (root / "source.py").write_text("result = eval(input)\n")
    negative = ci.execute(root, config.load(root), tmp_path / "negative")
    assert "extra.sast" in negative["failed"]
    findings = json.loads((tmp_path / "negative/extra-sast.log").read_text())["results"]
    assert {x["path"] for x in findings} == {"source.py", "source.js"}
