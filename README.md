# NDDev CI/CD Workflows

STD-0004 combines a modular CI/CD contract with the `nddev-cicd` Python implementation.
The normative edition and implementation are **0.1.0 draft**, pending owner acceptance.

The [CI composite](.github/actions/ci/action.yml) executes selected native profiles from a small
[caller contract](docs/usage.md). The [admission composite](.github/actions/admit/action.yml) resolves
capacity before a dependent job is allocated. The [delivery composite](.github/actions/deliver/action.yml)
consumes the exact successful PR run artifact after integration and coordinates one existing target.
Public consumers need Python/uv and their selected native tools; no private NDDev compiler or corpus
is used at runtime. Each callee resolves its own package separately from the caller checkout.

Start with [usage](docs/usage.md), [native profiles](docs/profiles.md), [AGENTS.md](AGENTS.md)
and the [normative descriptor](standard.yml). The normative source is [spec/](spec/).
Source validation runs on PR updates; delivery is a separate integrated `dev`/`main` push operation.
Public Linux uses standard hosted capacity. Private Linux uses caller-owned existing self-hosted jobs.
Windows/macOS paid-capable routes remain disabled without a confirmed compatible no-overage guarantee.

Native subprocess, report, filesystem, cache concurrency and HTTP static-delivery fixtures are exercised
by `uv run pytest`. Broad native-language fixtures and live pilot integration are being completed;
profile presence alone does not claim hardware, SDK, deployment or provider verification.
The source is [AGPL-3.0-only](LICENSE). See [origins](docs/origins.md) for the historical comparison.
