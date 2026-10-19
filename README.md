# NDDev CI/CD Workflows

STD-0004 combines a modular CI/CD contract with the `nddev-cicd` Python implementation.
The normative edition and implementation are **0.2.0 draft**, pending owner acceptance.

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
Public Windows/macOS also use standard GitHub-hosted runners. Private Windows/macOS require confirmed compatible no-overage admission.

`uv run pytest` exercises the shared runtime invariants. Native fixtures and the library source workflow
cover the 23 catalog families; `tests/run_native.py` drives language/tool fixtures while documentation
and workflow profiles validate the library itself. SDK preparation is in the PR workflow; the selected
OS cells are Linux x64, public Windows x64 Python and public Apple ARM Swift. Deliberate source,
report and dependency-graph failures are rejected. This is finite verification, not every SDK or OS.

`tests/native_delivery.py` exercises isolated HTTP, OCI/Compose, systemd, HTTPS package registry and
built Android APK targets. The systemd fixture requires an explicitly selected existing user manager;
mobile delivery consumes the actual Android build. No production device, registry or store is changed.
Integrated dev/main pushes separately validate native GitHub run/artifact lineage and install the
already-tested fixture artifact into a temporary loopback target. Source is not rebuilt after merging.
The source is [AGPL-3.0-only](LICENSE). See [origins](docs/origins.md) for the historical comparison.
