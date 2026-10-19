# Implementation origins

Generic native fixtures under `tests/native/{python,rust,go,cpp,qt,flutter,node,swift,r,sql,android}`
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

The JVM fixture is new. Its Maven only-script wrapper 3.3.4 was generated with the native Apache
Maven wrapper plugin, retaining the original script headers and upstream LICENSE/NOTICE alongside
its configuration. The distribution URL and SHA256 bind Maven 3.10.0; the official SHA512 was checked
when preparing this fixture. Its Java/JUnit/Checkstyle checks execute actual source, not recorded calls.

The R fixture uses the native renv 1.3.1 generated activation script. Its upstream Posit copyright
and MIT grant are retained in `tests/native/r/renv/`; the fixture package's original license remains.
The Android fixture retains the verified Gradle wrapper JAR with its embedded license, an external
copy of that license and its original script headers. The wrapper and distribution SHA256 values
were checked against the official Gradle 9.5.0 release. Its selected native target is Android API 36.

Generated Flutter web scaffolding/assets retain the Flutter SDK BSD notice in
`tests/native/flutter/FLUTTER-LICENSE`; the SDK version is declared by the native fixture.

The Rust fuzz target/lock and C++ libFuzzer harness additionally retain the original notices from
`NDDev-Technocracy-Archive/ci-workflows-20261014` at
`4b53916e8a7b1c2dd220766b6dd4170a843f622e` (`tests/fixtures/rust/fuzz/` and
`tests/fixtures/fuzzing/checksum_fuzzer.cpp`). Their grants remain in the adjacent NOTICE files.
The restored security/release/OCI entrypoints use maintained official tool/action interfaces;
no proprietary approval platform or paid capability tier is required. The new web example uses
native CSS-tree and Prettier because the inspected Stylelint dependency chain included an unpatched
high-severity braces vulnerability. Native package audit findings were resolved by changing tools,
not by suppressing the advisory or forcing an incompatible dependency override.
