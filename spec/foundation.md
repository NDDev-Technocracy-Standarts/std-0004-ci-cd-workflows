# Foundation

## R-0001 One public modular implementation

```item
strength: MUST
basis: owner
verification: review
criteria: Follow a public caller and a private cross-organization caller to the same actual implementation.
applies-when: The subject defines or distributes the reusable library.
```

The library MUST have one canonical implementation for each shared capability, with distinct CI,
build/artifact and CD responsibilities. Public reusable entrypoints contain no customer topology,
account records or credentials. A project composes only applicable profiles and capabilities;
using a technical module does not migrate its repository or require access to private NDDev tools.
Thin caller-owned jobs and reusable workflows use the same shared actions or native code rather
than independently maintained copies. No new orchestration, review or account-management service
is required by this standard.

## R-0002 Explicit legal ownership

```item
strength: MUST
basis: owner
verification: review
criteria: Compare LICENSE, metadata and the provenance/notices of reused files; no visibility-derived
  relicensing.
applies-when: The subject publishes or redistributes library material.
```

The public library MUST retain the selected AGPL-3.0-only terms and accurate notices for incorporated
material. SPDX declarations, package metadata and distributed files agree with the actual grant.
Private source, proprietary corpora and third-party material are not silently relicensed or published.
A repository's visibility alone neither selects a license nor grants redistribution rights.

## R-0003 Versioned and discoverable module contracts

```item
strength: MUST
basis: owner
verification: review
criteria: Check a supported caller, invalid input and compatible upgrade without a duplicated project
  recipe; inspect the caller's update channel and confirm every pinned source still resolves to a
  maintained origin.
sources:
- gha-reuse
- dependabot-options
applies-when: The subject supplies or adopts a module interface.
```

Each delivered module MUST expose its purpose, supported inputs, platform requirements, results and
limits. Project manifests and lockfiles remain the source for project-specific dependencies and
commands. Adopted workflow/action references identify immutable compatible source; updates are normal
reviewed changes, not a mutable main reference silently changing every consumer. Each consumer keeps
a scheduled update channel for those references, such as reviewed update proposals delayed by a
release cooldown, so pins follow current compatible releases. A reference to a retired, transferred
or unavailable source is a defect corrected by a reviewed migration, not a stable pin. Standard edition,
implementation version, runtime schema and consumer product version remain separate identities.

## R-0004 Visibility and platform select execution

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.routing]
criteria: Inspect the full job graph for public/private Linux and Windows/macOS, not only the build job.
sources:
- gha-reuse
- blacksmith-runners
- gha-hosted-runners
- gha-larger-runners
- runner-images
- gha-runs-on-contexts
- gha-rerun
applies-when: A job selects an execution provider or runner.
```

Every library job MUST follow the owner's execution routing, including routing, reporting and other
small helper jobs. Public Linux, Windows and macOS work uses compatible standard free GitHub-hosted runners; public
work never selects Blacksmith or private self-hosted capacity. Private work runs on the declared
NDDev self-hosted capacity. A private job names that capacity once, as a runner class (for example
`nddev-linux-small`, `nddev-linux`, `nddev-linux-arm-small` or `nddev-macos-small`), through the
library's route expression (`nddev-cicd route-expression <class>`), never as a hosted fallback label.
When a routed job has waited ten minutes for that capacity, the fleet controller moves its run to the
compatible Blacksmith runner. If Blacksmith does not start it or has no free allowance left, the
controller moves the run to the compatible standard GitHub-hosted runner. If that is refused as well,
the run waits for the self-hosted capacity again. Each move happens only under R-0005. The controller
owns the decision, the per-tier labels and the receipts; the workflow only reads them. A job that needs
the lane's own SDK, device or network keeps explicit self-hosted labels and is never moved. A failed
test is not retried on a different provider to obtain a passing result.
The repository that supplies a public workflow does not change the caller's billing or trust context.

On GitHub, public work selects only labels that GitHub lists as standard GitHub-hosted runners for
public repositories, which run without charge there. GitHub bills larger runners per minute even in
public repositories, so public work never selects them. Larger runners include `-large`, `-xlarge`,
multi-core (`-N-cores`) and GPU labels, and custom runner groups. Every job names an exact supported
image, such as `ubuntu-26.04`, `windows-2025` or `macos-15`, instead of a floating `-latest` label,
which changes image without a reviewed change. Linux release builds run on the image whose system
libraries match the systems they ship to. A label that GitHub announces for retirement is replaced
before its scheduled brownouts, because those brownouts already fail jobs.

## R-0005 Execution remains within zero additional spend

```item
strength: MUST
basis: owner
verification: review
criteria: Verify account-level cost enforcement and concurrent-run handling before any paid-capable dispatch.
sources:
- blacksmith-pricing
- blacksmith-runners
- blacksmith-settings
- gha-billing
- gha-limits
- gha-dependency-caching
- blacksmith-usage
applies-when: An invocation can consume provider or storage allowance.
```

A scheduled run MUST use a demonstrably free allowance or an existing self-hosted resource. Provider
quotas are interpreted in their actual billing units and ownership scope. An alert, card absence or
static estimate alone is not proof of a hard stop on charges. When free admission cannot be
established, the paid-capable route remains disabled; a genuinely free compatible route may be used.
No job buys resources, increases a spending limit or enables a paid add-on. The standards do not
require account churn, duplicate organizations or misrepresentation to obtain allowances.
Free capacity has concurrency limits per plan; on GitHub Free these are 20 concurrent standard jobs,
5 of them macOS. Work beyond the limit waits in the queue: a queue is not a reason to select paid
capacity or to remove checks. Storage stays inside the free allowances. The repository's hosted cache
allowance is not raised, because use beyond it is billed.
The private fallback of R-0004 is bounded the same way. Blacksmith states no hard stop for charges,
so the controller moves runs there only while the organization's measured usage stays inside
Blacksmith's free allowance. It moves runs to GitHub-hosted runners only while the organization's
included private minutes are not exhausted and usage beyond them is refused. Otherwise the run waits
for self-hosted capacity.

## R-0006 Runner selection precedes affected execution

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.routing]
criteria: Check unknown-label and cross-organization paths without accidentally scheduling a billed or
  private job.
sources:
- gha-reuse
- gha-composite
- gha-runs-on-contexts
applies-when: The implementation schedules a job or chooses execution capacity.
```

Routing MUST select only configured and available runner capabilities before the relevant job is
scheduled. Unknown platforms, malformed labels and missing capacity remain explicit outcomes, not
silent ubuntu-latest defaults. The caller owns its runner/job when cross-organization reusable
workflow access is insufficient; it may call a public composite implementation. Workflow source
selection and execution context cannot be controlled by untrusted payload fields. A declared runner
name is not evidence of its actual OS, architecture, toolchain or account entitlement.

A private job's runs-on is the canonical route expression, which reads only the controller's
organization variables (`NDDEV_ROUTE_LABELS`, `NDDEV_RUN_ROUTES`). A run without a route keeps its
class, so a manual re-run of an unmoved run stays on self-hosted capacity. `nddev-cicd runners-check
--visibility private` refuses hosted Linux labels and route expressions that differ from the canonical
one.

The routing helper validates configured labels and trust but does not query the native runner
inventory, job access or live queue. Its private self-hosted result reports this limitation
explicitly. Actual availability remains a caller-owned prerequisite established through the
existing runner inventory; label selection alone does not verify R-0006.
