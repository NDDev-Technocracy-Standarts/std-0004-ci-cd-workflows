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
  recipe.
sources:
- gha-reuse
applies-when: The subject supplies or adopts a module interface.
```

Each delivered module MUST expose its purpose, supported inputs, platform requirements, results and
limits. Project manifests and lockfiles remain the source for project-specific dependencies and
commands. Adopted workflow/action references identify immutable compatible source; updates are normal
reviewed changes, not a mutable main reference silently changing every consumer. Standard edition,
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
applies-when: A job selects an execution provider or runner.
```

Every library job MUST follow the owner's execution routing, including routing, reporting and other
small helper jobs. Public Linux, Windows and macOS work uses compatible standard free GitHub-hosted runners; public
work never selects Blacksmith or private self-hosted capacity. Private Linux work uses the declared
existing NDDev Linux self-hosted capacity, without hosted or Blacksmith overflow. Private Windows/macOS
work prefers compatible Blacksmith capacity and then compatible standard GitHub capacity only under R-0005. A failed test is not retried on a different provider to obtain a passing result.
The repository that supplies a public workflow does not change the caller's billing or trust context.

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
applies-when: An invocation can consume provider or storage allowance.
```

A scheduled run MUST use a demonstrably free allowance or an existing self-hosted resource. Provider
quotas are interpreted in their actual billing units and ownership scope. An alert, card absence or
static estimate alone is not proof of a hard stop on charges. When free admission cannot be
established, the paid-capable route remains disabled; a genuinely free compatible route may be used.
No job buys resources, increases a spending limit or enables a paid add-on. The standards do not
require account churn, duplicate organizations or misrepresentation to obtain allowances.

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
applies-when: The implementation schedules a job or chooses execution capacity.
```

Routing MUST select only configured and available runner capabilities before the relevant job is
scheduled. Unknown platforms, malformed labels and missing capacity remain explicit outcomes, not
silent ubuntu-latest defaults. The caller owns its runner/job when cross-organization reusable
workflow access is insufficient; it may call a public composite implementation. Workflow source
selection and execution context cannot be controlled by untrusted payload fields. A declared runner
name is not evidence of its actual OS, architecture, toolchain or account entitlement.

The routing helper validates configured labels and trust but does not query the native runner
inventory, job access or live queue. Its private self-hosted result reports this limitation
explicitly. Actual availability remains a caller-owned prerequisite established through the
existing runner inventory; label selection alone does not verify R-0006.
