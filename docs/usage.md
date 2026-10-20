# Consumer contract

Pin each external action/workflow to a reviewed full commit SHA. Keep a short gate on `pull_request` and full validation on `main` pushes.
A public main caller may use `.github/workflows/source.yml`; its explicit `uv` and `python` inputs own the project toolchain. Its facade pins a reviewed implementation
commit; use that exact implementation commit for `deliver` and inspect its `library-ref` output.
Require its `status` output to equal `success`;
its public-only contract deliberately exports no successful result for an inapplicable event/visibility.
The library's own CI demonstrates a direct composite caller. Do not use the public reusable workflow
for private execution: keep private jobs and their self-hosted labels in the caller, including planners
and final aggregation. Never grant public/fork code access to a private runner or deployment secret.

The CI action resolves `contract` inside `working-directory` (the checkout root by default).
A component can keep its contract at `backend/.github/nddev-ci.toml` and select
`working-directory: backend`. Separate invocations use unique `result-key` values; reusing an
existing result directory is refused. Select profiles with actual native
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
library's isolated runtime declared in the [CI action](../.github/actions/ci/action.yml). Tool provisioning belongs in job-local setup or the existing
runner owner. Project lockfiles remain authoritative. Environment values in the contract are nonsecret;
credentials belong in caller repository/environment secrets and are passed only to the operation that
needs them. Never pass deployment credentials to source checks.

`[artifacts] files = ["dist/*.whl", "dist/*.tar.gz"]` packages only explicit successful outputs.
The manifest binds bytes/modes, caller source/merge tree, lock/contract identities, run attempt and callee
code identity. The upload policy and bounded retention belong to the action inputs. Caches and credentials
are rejected. This is content/provenance binding, not a claim of signed SLSA attestation.

# Admission and delivery

Admission policy is trusted account configuration, never PR body labels or a remaining-balance guess.
Public Linux, Windows and macOS always use compatible standard GitHub-hosted runners. Private Linux
cannot fall back from self-hosted to hosted/Blacksmith. Private Windows/macOS try a verified compatible
Blacksmith no-overage route, then an equivalent admitted standard GitHub route.
An email alert is insufficient. A failing test is never rerun on another provider to obtain success.
Use `admit` outputs in a dependent job's `runs-on: fromJSON(...)` before that job exists.
For a private same-repository PR, `trusted_actors` selects the actual PR author's login, never
its rerunner. Include `dependabot[bot]` explicitly when approved; forks remain refused even for an
allowlisted author. Without this list, owner/member/collaborator association is required.
Private label selection reports `availability: not-checked`: it does not observe online runners,
repository access, busy runners or queue delay. Establish these from the existing native runner
inventory before dispatch; a valid label list alone does not establish runner availability.

Delivery follows completion of full main CI, using read-scoped Actions access. A trusted
`workflow_run` caller first invokes `eligible` with the source run ID, exact workflow and main
revision before checking out delivery code or preparing a target. It admits only a completed
successful same-repository main run that still identifies current main. Pass that run and a trusted
existing target JSON to `deliver`. Build and delivery use the same library SHA. The runtime verifies
the exact attempt, source tree and artifact bytes again before mutation; it does not rebuild them.
A project-owned server may build the payload, provided full main validation checks that exact
immutable payload or OCI digest and binds it to its native run/attempt before promotion. Source CI
for the same commit alone cannot validate a separately built binary. The built-in `deliver` path
expects the native verified source bundle; another server path must retain equivalent artifact
checks in its existing project workflow rather than claim that this adapter imported the artifact.
The historical PR-artifact integration mode remains available only through its explicit source
workflow selection for older adoptions.

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
references before acceptance or recovery. APK manifests are parsed by the selected SDK apkanalyzer. AAB structure and manifest are validated
by the pinned bundletool selected through BUNDLETOOL_JAR. Missing native tools block delivery.
IPA/XCArchive application metadata is inspected; signing remains explicitly unverified by this generic artifact adapter.
Native signing checks and any store submission need their separately authorized SDK/account path.

The bundled Rust fixture declares and executes its minimum compiler through native configuration and tests both its
default and declared alternate feature implementation. A consumer declaring a different MSRV selects
that actual installed compiler through its native job/extra commands; no unexecuted MSRV is inferred.

`package.commands` selects native argument arrays for installed console scripts, for example
`[["project-cli", "check"]]`. They execute inside the same isolated consumer environment outside the
checkout, using the actual caller interpreter. Every command must belong to the built distribution;
system executables or a source checkout cannot satisfy this installed-CLI check.

Trusted command strings use Bash with `-euo pipefail` on Unix and a supported PowerShell with native
error propagation on Windows. Prefer argument arrays for project-native data arguments. The Python
fixture exercises both successful quoting and an earlier failing process in a native shell pipeline.

Inside GitHub Actions, the admission CLI checks the actual caller event/repository visibility and
refuses a mismatched policy before emitting runner labels. Fork context cannot assert trusted private
capacity. Public reusable workflow ownership never supplies a private caller's billing entitlement.

## Existing remote targets over SSH

Set the delivery composite's optional `transport-config` input to a caller-owned JSON file:

```json
{"kind":"ssh","hostname":"deploy.example.invalid","user":"deploy","port":22,
 "identity_file":"/run/example/ssh.key","known_hosts":"/run/example/known_hosts","python":"python3"}
```

The caller materializes the private key and pinned known-host keys from GitHub repository secrets
into its job directory (key mode 0600); it supplies the target configuration separately. No key,
password or GitHub token is copied into the application artifact or installed on the target.
The transport ignores ambient SSH configuration/agents and enforces the supplied host key.

`target_directory`, native tools and health/version URLs belong to the remote environment. The
existing SSH user needs access to that target and its selected service/registry. The target provides
an interpreter satisfying the [package runtime requirements](../pyproject.toml) and compatible PyYAML; the adapter installs no system packages,
service or deployment daemon. Its selected module's native tools must already be available.

The CLI downloads and verifies the artifact from the exact eligible successful main run and attempt
before SSH transfer. It transfers the artifact, bindings and the same licensed implementation into
an owned temporary remote directory, then the target rechecks bytes/modes and performs preflight,
locking, mutations and health locally.
The receipt must match the tested artifact, revision and target generation. Concurrent callers use
the lock in the same remote target directory. A network failure is not permission to replay an
uncertain migration; reconcile the target's durable record and use the existing recovery contract.
Only transport staging is removed automatically; current/recovery releases remain target-owned.

`tests/native_remote.py` exercises a separate SSH server/container and filesystem through actual
SSH/SCP with pinned host identity, concurrent clients and failed-health recovery. The integrated
main completion smoke uses that same transport with its successful full-CI artifact. This is representative
remote transport acceptance, not a production deployment or a separate physical-server benchmark.

The optional `remote-environment` input names a caller-owned JSON file of explicitly selected native
settings/credentials, such as a registry token sourced from repository secrets. It is transferred only
inside private SSH staging and applied only to the authenticated adapter process; it is not included
in release files or receipts. Runner GitHub/SSH authority and interpreter/search-path controls are
refused. Existing systemd service secrets remain in their native target-owned environment mechanism.

## Public security and release modules

`public-security.yml` is a public source-analysis reusable module for main pushes and explicit legacy PR callers. It executes pinned native CodeQL,
SARIF finding thresholds, Dependency Review and community runner hardening. Enable the repository's
free dependency graph before selecting Dependency Review. The module grants no private Code Security
entitlement, starts no private hosted helper, and returns no successful status for an inapplicable event.
Its successful output means both the native analysis and the selected finding gates completed.

`prepare-release` consumes the exact eligible source run through the same library ref as source CI.
Its explicit file selection produces a mode-preserving candidate tar, source/asset bindings,
SHA256SUMS and native Syft SPDX inventory. Package containers are safely exposed to native catalogers;
the library does not invent a dependency list. Native cataloger support still bounds what can be
identified. Supporting metadata describes those limits; an SBOM is not a vulnerability-free certificate.

Public `release.yml` adds actual GitHub provenance and SBOM attestations, verifies both signatures,
and uploads the candidate plus offline bundles. It follows successful full main CI or explicit main
dispatch. It creates no tag or published release. Private free consumers use the preparation
composite on their existing Linux job without assuming private GitHub attestations are available.
Actions retention is bounded; retain an accepted/current candidate in the project's existing release
store before expiration. Payloads are promoted unchanged; source is not rebuilt after integration.

## Native OCI archives

`oci-build` creates an actual OCI archive and source/digest/compiler metadata. Its default Buildx
builder is uniquely owned and removed without changing the default/shared builder. An explicitly
selected existing builder retains its caller-owned storage/GC policy. This pinned SDK surface is
currently Linux x64; cross-platform builds still need the corresponding project SDK/runtime tests.
The builder exposes no deployment/registry credentials to source PR code.

Retain both `dist/image.oci.tar` and `dist/image.oci.json` in the source artifact. `oci-publish` then
downloads the exact integrated PR bundle and copies the archive through pinned native Skopeo without
rebuilding. Native inspection must confirm the same registry digest. It publishes a content-addressed
tag and returns `repository@sha256:...`; mutable channel aliases remain an independently coordinated
target operation. Caller secrets supply an explicit private registry auth file; optional native CA
material does not disable TLS verification. No registry/account/storage purchase is performed.

## Ready bounded advanced operations

Source-only shared helpers are available through both the CLI and native project stage/extra commands.
`@library` preserves explicit native arguments and resolves the same isolated implementation.
For example, after selecting a real native source profile and preparing its pinned nightly/tool SDK:

```toml
[extras.fuzz]
purpose="Bounded native fuzzing of the selected parser"
command=["@library","advanced-fuzz","--target","parser","--corpus","fuzz/corpus/parser","--runs","1000","--seconds","30"]
timeout=600
```

For fuzz/mutation helpers, omitting `--output` under CI allocates diagnostics inside the retained
source result directory, including real failing inputs. Canonical seed corpora are copied before
fuzzing. Rust uses a pinned installed nightly's actual rustc/cargo paths and a preserved fuzz lock;
libFuzzer consumes a caller-built native executable. The native LLVM build stage owns its compiler
identity. SDK absence, zero native executions and changed locks fail.

`advanced-mutation` runs native cargo-mutants, requires a successful unmutated baseline and complete
nonempty native outcomes, and applies the project's explicit missed-mutant budget. It retains native
logs/diffs/results. `benchmark-compare` reads actual paired pytest-benchmark JSON, requires matching
case/tool/machine/interpreter identities and positive native measurements, then applies the explicit
regression ratio. These capabilities add no universal coverage percentage, schedule or production load.

Before recursive source checks, native gitlink validation rejects stale, dirty, unavailable or
symlinked submodule worktrees. Callers initialize each required checkout using their existing scoped
credentials; the library does not delete stale worktrees or fetch arbitrary submodules automatically.
The same inputs are checked again before an aggregate can pass.

## Mechanical documentation scope

The existing documentation profile can select finite `documentation.style` path lists for authored,
generated, historical, literal and legal Markdown. Every tracked Markdown document then has one
explicit source role. An empty selector, conflicting ownership or an unclassified document fails.
Historical, fixture and legal exemptions require their actual source locations; an active README
cannot be hidden through a whole-file exemption.

Selected active text is checked for copied release values, fingerprints, transient claims, em dashes
and emoji. Native Markdown tokens distinguish links and code; identity checks also cover authored
comments, HTML attributes and fenced examples. Native link destinations retain their identities.
The check reports paths and mechanical categories without printing document content. It does not
establish factual correctness or semantic completeness. See this repository's
[native contract](../.github/nddev-ci.toml) for a selected example.


## Explicit native shapes and diagnostics

Impact paths use root-anchored POSIX globs: `*` stays within one path segment and `**` spans zero or
more segments. Exact native root lock names are shared inputs. A covered nested lock follows its component and
affected dependents; an uncovered path remains conservative. A source name containing `lock` is not
a shared lock. Explicit shared globs still take precedence. Fetch the comparison base explicitly or use
`fetch-depth: 0`; unavailable bases select every component. The `impact` composite exposes `selected`,
`not-applicable`, `profiles` and `base` as JSON. A dependent job can use
`if: contains(fromJSON(needs.impact.outputs.selected), 'backend')` before SDK/sidecar setup.

The security profile's default history scan requires `fetch-depth: 0` and a positive native scanned
commit count. A shallow checkout or a scanner that examined no commits fails. Machine Git output
ignores inherited global/system/config-injection settings and disables colour. Caller overrides of
security commands own their actual coverage and native finding thresholds.

Private Linux has a free Python route through the `tools` action's `security` capability. It
provisions checksum-verified Gitleaks/OSV and lock-resolved Bandit in job-owned storage. The security
profile defaults use these native tools with an explicit project policy, without CodeQL access:

```toml
[security]
python = ["src/**/*.py"]
licenses = ["MIT", "Apache-2.0"]
```

`python` scopes must each match tracked source. Bandit findings fail SAST; OSV checks lock-derived
dependencies and the caller's SPDX license allowlist. The sample licenses are illustrative, not a
legal grant or a universal allowlist. Missing scopes, missing policy, unavailable tools and scanner
errors fail. Other languages retain explicit free language-native `commands.security.sast` checks;
the Python default does not claim to analyze them. OSV uses its native advisory and deps.dev metadata
services. This route needs no paid GitHub security service and cannot waive required security stages.

Tracked locks at every depth are bound to the result and checked again after execution. Native
ecosystem names include JavaScript managers, Gradle and Swift. `[inputs] locks = ["config/tool.lock"]`
adds a project-specific tracked input; a selector matching nothing fails.
`[inputs.manifests] sql-data = ["database/revisions/*.py"]` names an actual migration layout.
Selectors must remain inside the selected project. Alembic, nested SQL/ORM migration scripts,
recursive shell scripts and named Dockerfile/Containerfile layouts are recognised directly.
Non-default layouts supply their real native lint/build/test commands.

Requirements-only Python applications provide explicit commands for each stage instead of invoking
package defaults against a nonexistent project. `[not_applicable.python]` can give bounded nonempty
reasons for `build` and `consumer`; `[not_applicable.typescript-javascript]` can explain `package`.
The result records `not-applicable` with its reason. Tests, setup and security cannot be waived.
A prerequisite that did not execute cannot satisfy a dependent native operation. Application image
or bundle packaging uses its real command; an unneeded wheel or registry package uses the declared
non-applicability. An empty command or successful no-op is not evidence of packaging.

JavaScript and web defaults resolve one native manager from `packageManager` and the tracked npm,
bun, pnpm or yarn lock. Conflicting managers fail. Frozen installation and script commands use that
manager. Node remains part of the toolchain even for bun; provision both when the project requires
Node-based tools. Non-npm package publication needs an explicit native command or allowed
non-applicability. Test scripts select their actual unit/browser scopes so bun does not collect
Playwright cases accidentally. The library neither provisions every SDK nor changes caller uv:
its own bootstrap uses an absolute verified executable outside caller PATH.

The Linux `tools` action accepts a space/comma-separated capability list, for example
`capability: security shell container`. Workflow tools include actionlint, lychee and zizmor;
security adds Gitleaks, OSV-Scanner and the locked Python SAST toolchain, shell adds Bats and ShellCheck. The native script validates
capabilities and verified owned binaries before reuse. SDKs and system libraries such as libmagic
belong to the runner owner or an explicit job-local caller setup. A caller setup verifies downloaded
packages against its trusted native package metadata and supplies only that job's library paths;
the shared action does not install packages into the host.

Non-success stages print a bounded diagnostic tail in the job log and an escaped summary detail.
`[diagnostics] tail_lines = 200` selects the limit, from zero to one thousand. Passing stages keep
full logs without flooding the console. Known secret environment values are redacted in exported
tails; caller-native masking and safe commands remain necessary for arbitrary private output.
Workflow-command processing is suspended while tails are printed.

The CI action accepts `upload: always`, `failure` or `never` and `retention-days` from one to three.
The compatibility default is `always`. Text results use artifact compression. `deliver`,
`oci-publish` and `prepare-release` need `always` on their source run because they consume its exact
bundle. A log-only caller can select failure-only upload or retain diagnostics in the native log.

Container and infrastructure contracts may declare `[commands.container] cleanup = [...]` or the
corresponding infrastructure command. Selected cleanup runs after success, failure, native timeout
or cooperative cancellation, and cleanup failure also fails the aggregate. It removes only resources
owned by that invocation. Use run ID, attempt and component in tags/container/network names.
A shared-host prune is not a cleanup contract. Runner termination can bypass process cleanup;
self-hosted callers also retain an `if: always()` recovery step scoped to those same resource IDs.

## Failure feedback and pin identity

The `feedback` composite accepts exact workflow paths and a creator allowlist, plus one completed
`run-id` or bounded reconciliation of recent completed runs. It needs `actions: read` and
`issues: write`. An optional `task-issue` receives deduplicated comments; otherwise one failure Issue
is created for each run attempt. Closed markers are reused and reruns have distinct attempt markers.
Markers are accepted only from the workflow bot or explicitly allowed actors. Missing pagination
coverage fails before publication. Reconciliation defaults to the native default branch and push, schedule and workflow_dispatch events
within seven days. `events` and `branches` explicitly select other cases, including PRs or a
workflow_run delivery handler; both filters also apply to an explicit run ID. `since` selects a UTC
lower bound within thirty days. `page-budget` bounds run-list API requests across all workflows,
branches and events; exhausted coverage fails before writing. Failed job names come from the exact
attempt's bounded native job metadata; `stale` is a supported failure conclusion.
All publishers in a repository share one concurrency group with
`cancel-in-progress: false`, so simultaneous event and reconciliation calls serialize.

A trusted `workflow_run` caller invokes the pinned action without checking out the failed candidate,
reading its artifacts or executing its code. Pass only the native run ID as data; paths, creator
allowlists and permissions come from trusted workflow configuration. The same bounded entrypoint
can serve an explicitly declared feedback schedule; it does not rerun source CI or repair code.
The owning agent still returns to native diagnostics and unresolved task work.

The native [runtime lock](../.github/runtime-lock.json) maps reviewed implementation and reusable workflow
commits independently. A draft pin has no invented release-tag comment. Published release notes
must identify both native refs; a standard edition tag alone does not identify the facade/backend
pair. The online zizmor job complements offline source analysis with read-only metadata checks.


## Validation phases

The short PR gate uses finite syntax, lint/type, relevant unit and critical secret checks. Full main
CI owns native builds, SDK/browser cells, package consumption, selected security and target readiness.
Each repository keeps its real commands in the existing workflow/contract, without a second gate
inventory. The convention is one stable `gate` aggregate in the existing PR workflow. It accounts
for every applicable premerge obligation and fails unexpected missing or skipped work. A native
main check with the same job name does not satisfy this phase.

`nddev-cicd eligible --phase pr --repository OWNER/REPO --workflow .github/workflows/ci.yml
--run-id RUN --revision HEAD --pull-request NUMBER --target dev` reads that existing aggregate.
It requires the exact PR event, current head, target/base, latest run and successful latest attempt;
pending, cancelled, missing, superseded or non-success evidence is refused. `--aggregate` supports
an existing different aggregate name without copying its check inventory. The result is read-only
evidence, not an atomic base lock: reconcile candidate and material base changes immediately before
an ordinary guarded merge under the adopted branch policy.

GitHub dev pushes perform neither full CI nor CD. An existing dev server builds dev
locally; repositories without one can still promote normally. A parent task remains open until its
applicable main validation and target acceptance finish.

A main impact contract declares `impact.baseline_workflow` as the exact full-validation workflow.
Its comparison starts at a completed successful ancestor obtained from bounded native run metadata.
Failed, pending and cancelled pushes cannot advance that baseline. Missing history or API coverage
selects every declared component. Shared inputs and dependency closure still apply. Superseding main
CI can cancel obsolete source work; target mutations use their existing lock and recovery rules.
A source-only repository has a package/documentation completion boundary and needs no invented server.
