"""Mechanical text scopes preserve native data and report only actual coverage."""

import pytest

from nddev_cicd import documentation
from nddev_cicd.model import Invalid, git


@pytest.mark.parametrize(
    "text,category",
    [
        ("An authored sentence\u2014with punctuation.\n", "decorative-prose"),
        ("A result \u2705\n", "decorative-prose"),
        ("Project version: 1.2.3\n", "release-value"),
        ("<!-- Version: 1.2.3 -->\n", "release-value"),
        ("```yaml\nimage: example/app@sha256:" + "a" * 64 + "\n```\n", "fingerprint"),
        ("Fingerprint: " + "b" * 40 + "\n", "fingerprint"),
        ("All 184 tests are passing on the latest build.\n", "transient-claim"),
    ],
)
def test_authored_identity_cannot_escape_in_comments_or_fences(repository, text, category):
    root = repository({"README.md": text})
    with pytest.raises(Invalid, match=category) as failure:
        documentation.check(root, {"style": {"authored": ["README.md"]}})
    assert "1.2.3" not in str(failure.value) and "a" * 40 not in str(failure.value)


def test_native_parser_scopes_and_literal_operators(repository):
    root = repository(
        {
            "README.md": "# Project\n\nFollow STD-0001 and R-0003; distance is 1.25 m.\n\n"
            "```sh\ngit diff --stat\n```\n\n[Native source](https://example.invalid/v1.2.3).\n",
            "example.yaml": "image: example/app@sha256:" + "a" * 64 + "\n",
            "tests/fixtures/original.md": "# Original\n\nRelease 1.2.3\n",
            "archive/original.md": "# Original\n\nAn earlier sentence\u2014retained.\n",
            "LICENSE.md": "License release 1.2.3\n",
            "generated/index.md": "# Index\n\n[Project](../README.md#project).\n",
        }
    )
    before = (root / "example.yaml").read_bytes()
    scope = {
        "authored": ["README.md"],
        "generated": ["generated/*.md"],
        "literal": ["tests/fixtures/*.md"],
        "historical": ["archive/*.md"],
        "legal": ["LICENSE.md"],
    }
    report = documentation.check(root, {"style": scope})
    assert report["style"]["files"] == 2 and report["style"]["preserved"] == 3
    assert (root / "example.yaml").read_bytes() == before


@pytest.mark.parametrize(
    "scope",
    [
        {"authored": ["missing.md"]},
        {"literal": ["README.md"]},
        {"historical": ["README.md"]},
        {"legal": ["README.md"]},
        {"unknown": ["README.md"]},
        {"authored": ["README.md"], "generated": ["README.md"]},
        {"authored": ["../README.md"]},
    ],
)
def test_empty_or_conflicting_scope_is_not_success(repository, scope):
    root = repository({"README.md": "# Project\n\nAn explanation.\n"})
    with pytest.raises(Invalid):
        documentation.check(root, {"style": scope})


def test_unclassified_markdown_is_not_an_active_allowlist(repository):
    root = repository({"README.md": "# Project\n", "docs/domain.md": "A domain.\n"})
    with pytest.raises(Invalid, match="unclassified"):
        documentation.check(root, {"style": {"authored": ["README.md"]}})
    assert documentation.check(root)["style"]["status"] == "not-selected"


def test_reference_links_images_and_anchors_use_native_tokens(repository):
    root = repository(
        {
            "README.md": "# Project\n\n[Guide][entry]\n\n[entry]: docs/guide.md#guide\n\n![result](image.svg)\n",
            "docs/guide.md": "# Guide\n\n## Same\n\n## Same\n\n[Duplicate](#same-1)\n",
            "image.svg": '<svg xmlns="http://www.w3.org/2000/svg"/>',
        }
    )
    assert documentation.check(root)["local_links"] == 3
    (root / "docs/guide.md").write_text("# Different\n")
    with pytest.raises(Invalid, match="anchor"):
        documentation.check(root)


def test_fenced_code_does_not_invent_a_document_link(repository):
    root = repository({"README.md": "# Project\n\n```md\n[example](missing.md)\n```\n"})
    assert documentation.check(root)["local_links"] == 0
    assert documentation.style_check(root, git(root, "ls-files", "-z").split("\0"), None) == {
        "status": "not-selected"
    }
