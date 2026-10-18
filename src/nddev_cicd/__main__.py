"""Thin command surface for the same shared operations used by composite entrypoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__, artifacts, ci, config, delivery, github, routing
from .model import Invalid, atomic_json


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="operation", required=True)
    run = sub.add_parser("ci", help="Execute selected native profiles and a complete result aggregate")
    run.add_argument("--root", type=Path, default=Path.cwd())
    run.add_argument("--contract", default=".github/nddev-ci.toml")
    run.add_argument("--output", type=Path, required=True)
    route = sub.add_parser("route", help="Choose admitted capacity before the affected job is allocated")
    route.add_argument("--policy", type=Path, required=True)
    pack = sub.add_parser("pack", help="Package exact selected files with source identity")
    pack.add_argument("--root", type=Path, default=Path.cwd())
    pack.add_argument("--files", nargs="+", required=True)
    pack.add_argument("--result", type=Path, required=True)
    pack.add_argument("--archive", type=Path, required=True)
    trust = sub.add_parser("eligible", help="Validate an exact successful PR run against its merged target")
    trust.add_argument("--repository", required=True)
    trust.add_argument("--run-id", type=int, required=True)
    trust.add_argument("--revision", required=True)
    trust.add_argument("--workflow", required=True)
    apply = sub.add_parser("apply", help="Apply one authorized typed native delivery module")
    apply.add_argument("--config", type=Path, required=True)
    apply.add_argument("--download", type=Path, required=True)
    apply.add_argument("--run-id", type=int, required=True)
    apply.add_argument("--workflow", required=True)
    reference = sub.add_parser("reference")
    reference.add_argument("--root", type=Path, default=Path.cwd())
    reference.add_argument("--check", action="store_true")
    for helper in ("package-check", "workflow-check"):
        helper_parser = sub.add_parser(helper)
        helper_parser.add_argument("--root", type=Path, default=Path.cwd())
        if helper == "package-check":
            helper_parser.add_argument("--contract")
    sub.add_parser("profiles", help="Print native profile contracts (no execution claim)")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.operation == "ci":
            root = args.root.resolve()
            contract = config.load(root, args.contract)
            result = ci.execute(root, contract, args.output.resolve())
            # Selected packaging is connected to actual successful source results, not a plan-only helper.
            if result["status"] == "success" and contract.get("artifacts", {}).get("files"):
                try:
                    result["artifact"] = artifacts.pack(
                        root,
                        contract["artifacts"]["files"],
                        args.output.resolve() / "artifact.tar.gz",
                        result["identity"],
                    )
                except (Invalid, OSError, ValueError) as error:
                    result.update(status="failure", artifact_error=str(error))
                atomic_json(args.output.resolve() / "result.json", result)
            print(
                json.dumps(
                    {
                        "status": result["status"],
                        "result": str(args.output / "result.json"),
                        "limitations": result.get("limitations", []),
                    }
                )
            )
            return 0 if result["status"] == "success" else 1
        if args.operation == "reference":
            from .reference import generate

            generate(args.root.resolve(), check=args.check)
            return 0
        if args.operation == "package-check":
            from .package_check import check

            settings = (
                config.load(args.root.resolve(), args.contract).get("package", {}) if args.contract else {}
            )
            check(args.root.resolve(), settings)
            return 0
        if args.operation == "workflow-check":
            from .workflow_check import check

            check(args.root.resolve())
            return 0
        if args.operation == "profiles":
            result = config.catalog()
        elif args.operation == "route":
            result = routing.select(**json.loads(args.policy.read_text()))
        elif args.operation == "pack":
            evidence = json.loads(args.result.read_text())
            if evidence.get("status") != "success":
                raise Invalid("Do not package a failed/unavailable source result")
            result = artifacts.pack(args.root.resolve(), args.files, args.archive, evidence["identity"])
        elif args.operation == "eligible":
            result = github.eligible(args.repository, args.run_id, args.revision, args.workflow)
        else:
            if os.environ.get("GITHUB_EVENT_NAME") != "push" or os.environ.get("GITHUB_REF") not in {
                "refs/heads/dev",
                "refs/heads/main",
            }:
                raise Invalid(
                    "CD CLI requires an authorized integrated dev/main push; PR events cannot apply"
                )
            repository, revision = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_SHA", "")
            archive, manifest, expected = github.bundle(
                repository, args.run_id, revision, args.workflow, args.download
            )
            result = delivery.apply(
                archive, manifest, expected, json.loads(args.config.read_text()), authorized=True
            )
        print(json.dumps(result, indent=2))
        return 0
    except (Invalid, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
