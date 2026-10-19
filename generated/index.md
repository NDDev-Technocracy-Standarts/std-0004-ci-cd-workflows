<!-- Generated from canonical sources. Do not edit. -->

# std-0004 item index

Select a requirement to read its statement and applicability. Verification bindings describe
mechanical coverage and do not replace semantic review.

| ID | Principle |
|---|---|
| [P-0001](../spec/intent.md) | Complete feedback at the smallest sufficient cost |

| ID | Strength | Title | Applies | Verification | Verified by |
|---|---|---|---|---|---|
| [R-0001](../spec/foundation.md) | MUST | One public modular implementation | condition (item): The subject defines or distributes the reusable library. | review | None |
| [R-0002](../spec/foundation.md) | MUST | Explicit legal ownership | condition (item): The subject publishes or redistributes library material. | review | None |
| [R-0003](../spec/foundation.md) | MUST | Versioned and discoverable module contracts | condition (item): The subject supplies or adopts a module interface. | review | None |
| [R-0004](../spec/foundation.md) | MUST | Visibility and platform select execution | condition (item): A job selects an execution provider or runner. | partial | `runtime.routing` |
| [R-0005](../spec/foundation.md) | MUST | Execution remains within zero additional spend | condition (item): An invocation can consume provider or storage allowance. | review | None |
| [R-0006](../spec/foundation.md) | MUST | Runner selection precedes affected execution | condition (item): The implementation schedules a job or chooses execution capacity. | partial | `runtime.routing` |
| [R-0007](../spec/ci.md) | MUST | Pull requests own source validation | condition (item): The subject defines or invokes source-validation CI. | review | None |
| [R-0008](../spec/ci.md) | MUST | Selected coverage includes affected dependents | condition (item): The subject determines applicable validation coverage. | partial | `runtime.impact` |
| [R-0009](../spec/ci.md) | MUST | Passing means the expected work ran | condition (item): The subject summarizes or gates validation results. | partial | `runtime.reports` |
| [R-0010](../spec/ci.md) | MUST | Results identify their actual inputs | condition (item): The subject records, compares or reuses validation results. | partial | `runtime.inputs`, `runtime.gitlinks` |
| [R-0011](../spec/ci.md) | MUST | Toolchains and language profiles are real | condition (item): A language or SDK profile is selected. | partial | `runtime.profiles`, `runtime.advanced` |
| [R-0012](../spec/ci.md) | MUST | Quality gates have stable meanings | condition (item): The subject applies quality or security gates. | partial | `runtime.gates` |
| [R-0013](../spec/ci.md) | MUST | Architecture checks enforce actual boundaries | condition (item): The project selects an architectural boundary check. | partial | `runtime.architecture` |
| [R-0014](../spec/ci.md) | MUST | Documentation feedback follows executable sources | condition (item): The subject checks or updates implementation documentation. | partial | `runtime.documents` |
| [R-0015](../spec/ci.md) | MUST | Untrusted checks do not inherit delivery authority | condition (item): The subject executes repository code or crosses CI/CD trust boundaries. | review | None |
| [R-0016](../spec/performance.md) | MUST | Failures survive wrappers and shell pipelines | condition (item): A wrapper or dependent operation executes commands. | partial | `runtime.process` |
| [R-0017](../spec/performance.md) | MUST | Optimization preserves obligations | condition (item): The subject changes execution efficiency or parallelism. | review | None |
| [R-0018](../spec/performance.md) | MUST | Caches have owners and bounded lifetimes | condition (item): The subject reads, writes or reclaims acceleration state. | partial | `runtime.cache` |
| [R-0019](../spec/performance.md) | MUST | Reports remain useful without storage duplication | condition (item): The subject exports or retains run diagnostics or artifacts. | partial | `runtime.retention` |
| [R-0020](../spec/delivery.md) | MUST | CD consumes an eligible integrated result | condition (item): The subject determines eligibility for deployment. | partial | `runtime.lineage` |
| [R-0021](../spec/delivery.md) | MUST | Artifact promotion preserves identity | condition (item): A build artifact is produced, published or promoted. | partial | `runtime.artifact`, `runtime.release`, `runtime.oci` |
| [R-0022](../spec/delivery.md) | MUST | Native deployment is complete rather than declarative only | condition (item): The project selects a deployment adapter. | partial | `runtime.delivery`, `runtime.preflight`, `runtime.current`, `runtime.remote` |
| [R-0023](../spec/delivery.md) | MUST | The target serializes deployment | condition (item): The subject can mutate a shared delivery target. | partial | `runtime.target-lock`, `runtime.remote` |
| [R-0024](../spec/delivery.md) | MUST | Recovery respects data and partial state | condition (item): Delivery changes data or encounters partial execution or failure. | partial | `runtime.recovery` |
| [R-0025](../spec/delivery.md) | MUST | Acceptance identifies the running result | condition (item): The invocation claims a delivered result. | partial | `runtime.health` |
| [R-0026](../spec/maintenance.md) | MUST | The library is usable outside its publisher account | condition (item): The library exposes public technical entrypoints. | review | None |
| [R-0027](../spec/maintenance.md) | MUST | Claims of support match real verification | condition (item): The implementation declares capabilities or verification coverage. | review | None |
| [R-0028](../spec/maintenance.md) | MUST | Adoption and cleanup have a finite scope | condition (item): The task adopts or replaces workflows or related integrations. | review | None |
