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
    impact = sub.add_parser("impact", help="Expose the same conservative plan before dependent jobs allocate")
    impact.add_argument("--root", type=Path, default=Path.cwd())
    impact.add_argument("--contract", default=".github/nddev-ci.toml")
    impact.add_argument("--base")
    impact.add_argument("--head")
    feedback = sub.add_parser("feedback", help="Publish bounded metadata-only failure feedback")
    feedback.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    feedback.add_argument("--workflows", required=True, help="JSON array of exact workflow paths")
    feedback.add_argument("--creators", required=True, help="JSON array of allowed run creators")
    feedback.add_argument(
        "--conclusions", default='["failure","timed_out","action_required","startup_failure"]'
    )
    feedback.add_argument("--run-id", type=int)
    feedback.add_argument("--task-issue", type=int)
    secret = sub.add_parser("secrets-check", help="Verify a real full-history scan for a short native gate")
    secret.add_argument("--root", type=Path, default=Path.cwd())
    secret.add_argument("--output", type=Path)
    route = sub.add_parser("route", help="Choose admitted capacity before the affected job is allocated")
    route.add_argument("--policy", type=Path, required=True)
    pack = sub.add_parser("pack", help="Package exact selected files with source identity")
    pack.add_argument("--root", type=Path, default=Path.cwd())
    pack.add_argument("--files", nargs="+", required=True)
    pack.add_argument("--result", type=Path, required=True)
    pack.add_argument("--archive", type=Path, required=True)
    trust = sub.add_parser(
        "eligible", help="Validate an exact successful source run against its integrated target"
    )
    trust.add_argument("--repository", required=True)
    trust.add_argument("--run-id", type=int, required=True)
    trust.add_argument("--revision", required=True)
    trust.add_argument("--workflow", required=True)
    apply = sub.add_parser("apply", help="Apply one authorized typed native delivery module")
    apply.add_argument("--config", type=Path, required=True)
    apply.add_argument("--download", type=Path, required=True)
    apply.add_argument("--run-id", type=int, required=True)
    apply.add_argument("--workflow", required=True)
    apply.add_argument(
        "--transport-config",
        type=Path,
        help="Optional trusted SSH transport JSON; target commands execute remotely",
    )
    apply.add_argument(
        "--remote-environment",
        type=Path,
        help="Optional caller-owned JSON of selected target credentials/settings",
    )
    release = sub.add_parser(
        "prepare-release", help="Prepare a native release candidate from an eligible integrated artifact"
    )
    release.add_argument("--run-id", type=int, required=True)
    release.add_argument("--workflow", default=".github/workflows/main-ci.yml")
    release.add_argument("--download", type=Path, required=True)
    release.add_argument("--directory", type=Path, required=True)
    release.add_argument(
        "--files", required=True, help="JSON list of selected native package/artifact patterns"
    )
    image = sub.add_parser(
        "oci-build", help="Build an actual OCI archive without publishing source PR credentials"
    )
    image.add_argument("--root", type=Path, default=Path.cwd())
    image.add_argument("--output", default="dist/image.oci.tar")
    image.add_argument("--context", default=".")
    image.add_argument("--dockerfile", default="Dockerfile")
    image.add_argument("--platforms", default="linux/amd64")
    image.add_argument("--builder")
    publish = sub.add_parser(
        "oci-publish", help="Publish the exact eligible OCI archive to an existing registry"
    )
    publish.add_argument("--run-id", type=int, required=True)
    publish.add_argument("--workflow", default=".github/workflows/main-ci.yml")
    publish.add_argument("--download", type=Path, required=True)
    publish.add_argument("--image-file", default="dist/image.oci.tar")
    publish.add_argument("--metadata-file", default="dist/image.oci.json")
    publish.add_argument("--repository", required=True)
    publish.add_argument("--auth-file", type=Path)
    publish.add_argument("--certificates", type=Path)
    heavy = sub.add_parser("advanced-fuzz", help="Run a real bounded native cargo-fuzz/libFuzzer target")
    heavy.add_argument("--root", type=Path, default=Path.cwd())
    heavy.add_argument("--output", type=Path, required=True)
    heavy.add_argument("--engine", choices=["rust", "libfuzzer"], default="rust")
    heavy.add_argument("--target", required=True)
    heavy.add_argument("--corpus", required=True)
    heavy.add_argument("--runs", type=int, default=1000)
    heavy.add_argument("--seconds", type=int, default=30)
    heavy.add_argument("--toolchain", default="nightly-2026-10-19")
    mutation = sub.add_parser(
        "advanced-mutation", help="Run actual cargo-mutants with native result accounting"
    )
    mutation.add_argument("--root", type=Path, default=Path.cwd())
    mutation.add_argument("--output", type=Path, required=True)
    mutation.add_argument("--maximum-missed", type=int, default=0)
    mutation.add_argument("--timeout", type=int, default=15)
    compare = sub.add_parser("benchmark-compare", help="Compare real paired pytest-benchmark measurements")
    compare.add_argument("--root", type=Path, default=Path.cwd())
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--candidate", type=Path, required=True)
    compare.add_argument("--maximum-ratio", type=float, required=True)
    reference = sub.add_parser("reference")
    reference.add_argument("--root", type=Path, default=Path.cwd())
    reference.add_argument("--check", action="store_true")
    for helper in ("package-check", "workflow-check"):
        helper_parser = sub.add_parser(helper)
        helper_parser.add_argument("--root", type=Path, default=Path.cwd())
        if helper == "package-check":
            helper_parser.add_argument("--contract")
    sarif = sub.add_parser("sarif-check", help="Gate actual native public CodeQL findings")
    sarif.add_argument("--directory", type=Path, required=True)
    sarif.add_argument("--minimum", default="moderate")
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
        if args.operation == "secrets-check":
            root = args.root.resolve()
            output = (
                args.output
                or Path(os.environ.get("NDDEV_RESULT_DIR", str(root / ".nddev-reports"))) / "secret-scan"
            )
            result = ci.secrets_check(root, output.resolve())
            print(json.dumps(result))
            return 0 if result["status"] == "success" else 1
        if args.operation == "impact":
            root = args.root.resolve()
            selected, plan = ci.selection(root, config.load(root, args.contract), args.base, args.head)
            if plan is None:
                raise Invalid("The impact entrypoint requires declared components")
            result = {
                "profiles": selected,
                "selected": plan["selected_components"],
                "not_applicable": plan["not_applicable"],
                "base": plan["base"],
            }
            print(json.dumps(result))
            return 0
        if args.operation == "feedback":
            from .feedback import publish

            result = publish(
                args.repository,
                json.loads(args.workflows),
                json.loads(args.creators),
                run_id=args.run_id,
                task_issue=args.task_issue,
                conclusions=json.loads(args.conclusions),
            )
            print(json.dumps(result))
            return 0
        if args.operation == "sarif-check":
            from .reports import sarif

            result = sarif(args.directory, args.minimum)
            print(json.dumps(result, indent=2))
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
            result = routing.select(**routing.caller_policy(json.loads(args.policy.read_text())))
        elif args.operation == "pack":
            evidence = json.loads(args.result.read_text())
            if evidence.get("status") != "success":
                raise Invalid("Do not package a failed/unavailable source result")
            result = artifacts.pack(args.root.resolve(), args.files, args.archive, evidence["identity"])
        elif args.operation == "eligible":
            result = github.eligible(args.repository, args.run_id, args.revision, args.workflow)
        elif args.operation in {"advanced-fuzz", "advanced-mutation", "benchmark-compare"}:
            from . import advanced

            if args.operation == "advanced-fuzz":
                result = advanced.fuzz(
                    args.root.resolve(),
                    args.output.resolve(),
                    args.target,
                    engine=args.engine,
                    corpus=args.corpus,
                    runs=args.runs,
                    seconds=args.seconds,
                    toolchain=args.toolchain,
                )
            elif args.operation == "advanced-mutation":
                result = advanced.mutation(
                    args.root.resolve(),
                    args.output.resolve(),
                    maximum_missed=args.maximum_missed,
                    timeout=args.timeout,
                )
            else:
                result = advanced.benchmark(args.baseline, args.candidate, args.maximum_ratio)
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "success" else 1
        elif args.operation == "oci-build":
            from . import oci

            result = oci.build(
                args.root,
                args.output,
                context=args.context,
                dockerfile=args.dockerfile,
                platforms=args.platforms,
                builder=args.builder,
            )
        elif args.operation == "oci-publish":
            from . import oci
            from .model import contained

            revision = github.authorized_revision(args.run_id, args.workflow)
            archive, manifest, expected = github.bundle(
                os.environ.get("GITHUB_REPOSITORY", ""),
                args.run_id,
                revision,
                args.workflow,
                args.download,
            )
            payload = args.download / "verified-payload"
            artifacts.unpack(archive, manifest, payload, expected)
            result = oci.publish(
                contained(payload, args.image_file, exists=True),
                json.loads(contained(payload, args.metadata_file, exists=True).read_text()),
                expected,
                args.repository,
                auth=args.auth_file,
                certificates=args.certificates,
            )
        elif args.operation == "prepare-release":
            from . import release

            revision = github.authorized_revision(args.run_id, args.workflow, allow_dispatch=True)
            archive, manifest, expected = github.bundle(
                os.environ.get("GITHUB_REPOSITORY", ""),
                args.run_id,
                revision,
                args.workflow,
                args.download,
            )
            result = release.prepare(archive, manifest, expected, args.directory, json.loads(args.files))
        else:
            revision = github.authorized_revision(args.run_id, args.workflow)
            repository = os.environ.get("GITHUB_REPOSITORY", "")
            archive, manifest, expected = github.bundle(
                repository, args.run_id, revision, args.workflow, args.download
            )
            target = json.loads(args.config.read_text())
            if args.transport_config:
                from . import remote

                result = remote.apply(
                    archive,
                    manifest,
                    expected,
                    target,
                    json.loads(args.transport_config.read_text()),
                    authorized=True,
                    environment=json.loads(args.remote_environment.read_text())
                    if args.remote_environment
                    else None,
                )
            else:
                if args.remote_environment:
                    raise Invalid("Remote environment input requires the explicit SSH transport")
                result = delivery.apply(archive, manifest, expected, target, authorized=True)
        print(json.dumps(result, indent=2))
        return 0
    except (Invalid, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
