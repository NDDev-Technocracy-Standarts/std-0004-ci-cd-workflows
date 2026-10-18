# Implementation origins

Generic native fixtures under `tests/native/{python,rust,go,cpp,qt,flutter,node,swift,r,sql}`
were imported from the public `NDDev-Technocracy-Archive/ci-workflows` exact source
`481fc9e5e8411106a1f6effcd9372784b0f3f245`, originally at corresponding `tests/fixtures/` paths.
Their original [notice](../tests/native/NOTICE), copyright and AGPL-3.0-or-later grant are retained.
The repository's own new code remains AGPL-3.0-only; no imported grant is narrowed. Existing
fixture-specific package license declarations are preserved. Fixtures are adapted to execute real
selected tests; an old example without native tests does not count as a successful test lane.

The separately identified archived `ci-workflows-20261014` and `cd-workflows` were also inspected.
The shared runtime and composite entrypoints are newly implemented here. The earlier policy/evidence
platforms, paid capability tiers, deployment approval/state machine and hosted private Linux prelude
are not imported. External actions remain separately licensed dependencies pinned to maintained
full commits, with their original notices retained by their distributions. No archive release or
existing consumer is changed.

Canonical standard compilation uses the authorized STD-0000 tool in its private integration path.
Public runtime installation, native tests and consumer invocation do not require that tool or any
private corpus. Compiler-generated output here derives from this repository's own normative source.
