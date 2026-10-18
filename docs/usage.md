# Consumer contract

Pin each external action/workflow to a reviewed full commit SHA. Keep source jobs on `pull_request`.
A public caller may use `.github/workflows/source.yml`. Its facade pins a reviewed implementation
commit; use that exact implementation commit for `deliver` and inspect its `library-ref` output.
Require its `status` output to equal `success`;
its public-only contract deliberately exports no successful result for an inapplicable event/visibility.
The library's own CI demonstrates a direct composite caller. Do not use the public reusable workflow
for private execution: keep private jobs and their self-hosted labels in the caller, including planners
and final aggregation. Never grant public/fork code access to a private runner or deployment secret.

The CI action reads `.github/nddev-ci.toml` in the caller checkout. Select profiles with actual native
manifests and all relevant extras. For example, a Python package with architectural contracts selects
`profiles = ["python", "architecture"]`; its architecture configuration declares nonempty source scopes
and the native dependency command (such as Import Linter). Exact stage names and defaults are generated
in [profiles](profiles.md). A required native command with no default fails until supplied.

`[commands.PROFILE]` overrides native command arrays or intentional trusted shell commands. Use arrays
for data arguments. `[reports.PROFILE]` selects native JUnit/TRX/Go/Cargo/Dart or explicitly documented
positive-count report parsing. Zero tests, stale/empty/all-skipped reports and missing selected stages
fail. `[timeouts]` bounds native operations in seconds. `[extras.NAME]` requires a purpose, command and
finite timeout. Use extras for project-selected race/property/fuzz/mutation/browser/accessibility,
feature/MSRV or compatibility checks; preserve retained failing inputs in selected artifacts.

The CI action's `python` input sets the caller's actual uv interpreter selection independently from the
library's isolated Python 3.13 environment. Tool provisioning belongs in job-local setup or the existing
runner owner. Project lockfiles remain authoritative. Environment values in the contract are nonsecret;
credentials belong in caller repository/environment secrets and are passed only to the operation that
needs them. Never pass deployment credentials to source checks.

`[artifacts] files = ["dist/*.whl", "dist/*.tar.gz"]` packages only explicit successful outputs.
The manifest binds bytes/modes, caller source/merge tree, lock/contract identities, run attempt and callee
code identity. GitHub stores the small selected bundle with three-day retention. Caches and credentials
are rejected. This is content/provenance binding, not a claim of signed SLSA attestation.

# Admission and delivery

Admission policy is trusted account configuration, never PR body labels or a remaining-balance guess.
Linux visibility routing cannot fall back from private self-hosted to hosted/Blacksmith. Windows/macOS
try a verified compatible Blacksmith no-overage route, then an equivalent admitted standard GitHub route.
An email alert is insufficient. A failing test is never rerun on another provider to obtain success.
Use `admit` outputs in a dependent job's `runs-on: fromJSON(...)` before that job exists.

Delivery runs only on integrated `dev`/`main` pushes, with a read-scoped `GITHUB_TOKEN` able to read
Actions artifacts and PR metadata. Pass the completed PR source run ID, exact source workflow path and
a trusted existing target JSON file to `deliver`. Build and delivery use the same library SHA. The
runtime downloads the exact attempt's native artifact, rejects failed/unrelated/superseded runs and
requires the integrated source tree to equal the tested tree. It does not rebuild source after merging.

Target configuration selects one of `static-web`, `systemd-binary`, `compose`, `packages`,
`mobile-artifacts`; an existing `target_directory`; a monotonically increasing target-owner `generation`;
and `expected_previous` artifact identity (`null` on first delivery). The target lock serializes actual
mutations, and stale generations cannot replace newer state. Final release directories are distinct
from compiler/download caches. Keep current and needed rollback artifacts.

Static/systemd targets activate exact versioned files through `current`; the existing web server or
service must already use that location. Configure a meaningful health_url and expected scenario content. The response must also contain the
tested revision; use version_url for a separate native version endpoint when needed. Builds receive
NDDEV_TESTED_REVISION and NDDEV_TESTED_TREE for this identity. A generic successful health response
cannot establish the deployed revision.
Systemd selects one existing service. Compose selects an existing stable project and actual services,
uses immutable image digests and `up --wait --no-build`. Package publication selects an existing HTTPS
registry and native Python/npm/NuGet publisher; secrets and registry verification remain caller-owned.
Mobile delivery validates configured artifact files and makes no store-submission claim.

Data mutations require existing backup/recovery or an explicit scoped backup waiver. A failed/partial
operation remains pending; the library never blindly retries it. After the target owner reconciles its
actual state, `recover_partial: true` can verify the same installed artifact and actual health before
completing the record. Registry/mobile recovery additionally requires a native `reconcile_command`.
Automatic file rollback is allowed only when explicitly compatible and no data migration occurred;
service/data recovery is still verified. No production target is invented by the source-only pilots.

# Packages and owned caches

The Python consumer accepts a contained package.directory (default dist) and optional explicit
package.imports for namespace/root-layout packages. It consumes the built wheel outside the checkout
using the actual caller interpreter and locked runtime dependencies, separately from the library.
A failed build makes a dependent consumer/package test unavailable; stale outputs cannot establish
that the failed candidate built.

Set NDDEV_CACHE_ROOT only for an owned Rust cache and declare cache_budget_bytes,
cache_min_free_bytes, cache_ttl_seconds in the rust table. Reclamation touches only inactive matching
namespaces, with a measured free-disk reserve. This is a retention budget and admission check, not a
filesystem quota. Compiler stores, Cargo downloads/intermediates and retained final packages have
distinct locations/controls. The default root Cargo package is staged into dist before cache cleanup;
workspace/custom packaging uses its native project command.

Native Cargo target reuse works independently from optional sccache=true. Sccache disables Rust
incremental compilation, holds the store lock for its complete server lifetime and stops that owned
server before reclamation. Its compiler-store limit is half the declared budget, at most 2GiB.
A failed stop protects the namespace for owner reconciliation. Windows uses the native Cargo cache;
this local sccache mode currently requires Unix sockets. No shared-host prune or routine cargo clean
is used. Native feature/MSRV/cross-target checks are selected native stage/extra commands.

A caller-owned monorepo job can select an existing contained working-directory; the callee package
continues to resolve from its own action path. Private admission labels include self-hosted, Linux
and the selected actual architecture. A requested architecture cannot be inferred from a prose host name.

For native external-link checks, documentation.external_link_report can point to the actual Lychee
JSON output. An explicit documentation.network_timeouts URL-to-Issue map classifies only those native
timeouts as advisory unavailable results. The aggregate retains them in limitations and never claims
the URL was verified. Broken URLs, malformed/missing reports and unlisted timeouts remain blocking.
No scanner/test failure is converted into a successful check.

Documentation may exclude an exact historical directory with a trailing-slash `exclude` entry.
Current source links stay checked. `network_outages` maps native connection failures/timeouts to an
actual Issue; `access_outages.URL` requires the exact 403/429 status, reason and Issue. These remain
unavailable in results and limitations. HTTP 404 and other broken responses cannot use this path.

Target JSON rejects unknown or inapplicable fields. Pending recovery binds the same module/resource
selectors, artifact and generation; correcting a health endpoint does not retarget a service/project.
Compose uses `--no-deps` for precisely selected services and inspects their running immutable image
references before acceptance or recovery. APK/AAB native manifests and IPA/XCArchive application
metadata are inspected; signing remains explicitly unverified by this generic artifact adapter.
Native signing checks and any store submission need their separately authorized SDK/account path.

The bundled Rust fixture declares and executes Rust 1.99.0 as its minimum compiler and tests both its
default and declared alternate feature implementation. A consumer declaring a different MSRV selects
that actual installed compiler through its native job/extra commands; no unexecuted MSRV is inferred.
