# Ci

## R-0007 Pull requests own source validation

```item
strength: MUST
basis: owner
verification: review
criteria: Map triggers to the task/dev/main flow; push-only source validation and hidden schedules are
  absent.
sources:
- gha-events
applies-when: The subject defines or invokes source-validation CI.
```

Source-validation CI MUST run for applicable pull-request candidates, including relevant updates,
without a duplicate branch-push or scheduled full-CI path. Promotion PRs target the required dev/main
composition. CD on accepted integration events is separate and may perform target verification.
A manual retry or reproduction is tied to a specific authorized PR or failed attempt; it is not a
hidden parallel periodic CI system. No unrelated runner is provisioned merely because a PR exists.

This baseline consumes the branch and acceptance policy owned by the adopted GitHub workflow
standard. A main-only integration flow or nonblocking post-merge source validation needs an explicit
scoped owner departure for the affected requirements; a different trigger alone does not establish
conformance. A declared narrow schedule for advisory refresh, owned registry reclamation or failure
feedback is not duplicate source validation. Its purpose, owner, selected inputs and finite budget
remain explicit. An undeclared purpose or a second periodic full-CI path is a hidden schedule.

## R-0008 Selected coverage includes affected dependents

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.impact]
criteria: Exercise shared-input, rename, deleted-file and missing-base changes against real selected components.
sources:
- gha-events
applies-when: The subject determines applicable validation coverage.
```

The run MUST identify its selected profiles and all affected obligations, including dependent
components, shared locks, generated contracts and behavior-changing build configuration. Deletions,
renames and unavailable comparison bases do not produce a false empty change set. An uncertain
impact calculation conservatively retains required coverage or fails explicitly. Selected expensive
checks use finite project-appropriate budgets and relevant PR conditions; required coverage is not
moved to an unobserved future run solely to make a PR fast.

## R-0009 Passing means the expected work ran

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.reports, runtime.consumer-contracts]
criteria: Inject a missing report, zero-test result and skipped required job; the aggregate cannot pass.
applies-when: The subject summarizes or gates validation results.
```

An aggregate success MUST account for every expected result for this candidate. No tests discovered,
a missing report, an unsupported selected target, a tool startup failure and an unexpected skipped
job are not passed checks. Non-applicability is distinguishable from inability to execute. Optional
checks are optional because the project contract says so, not because they failed. Success summaries
name what actually ran rather than repeat requested versions or capabilities.

## R-0010 Results identify their actual inputs

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.inputs, runtime.gitlinks]
criteria: Distinguish changed base, changed library and unchanged deterministic inputs without fabricating
  a green status.
applies-when: The subject records, compares or reuses validation results.
```

Reusable results MUST identify the source candidate and significant validation inputs sufficiently
to prevent reuse for a different change. Head/base or tested merge context, workflow implementation,
locks, selected configuration and platform matter where they affect the result. Cache hits and a
matching branch name do not establish check success. Expired vulnerability data and time-dependent
checks retain their own freshness semantics. Identical input results may be reused without ritual
repetition; material changes require the corresponding affected check.

## R-0011 Toolchains and language profiles are real

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.profiles, runtime.advanced]
criteria: Run native positive and failure fixtures for claimed profiles and inspect actual tool/version
  outputs.
applies-when: A language or SDK profile is selected.
```

A language or SDK profile MUST execute its selected native build, analysis, test and packaging
operations with compatible resolved toolchains. It verifies the interpreter/compiler that actually
runs and honors project locks without silently rewriting them. Installed tools, caller commands and
platform-specific behavior are handled explicitly. The capability catalog differentiates native
execution, cross-compilation and unverified hardware; declaring a language in YAML is not support.

## R-0012 Quality gates have stable meanings

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.gates]
criteria: Check representative blocking and advisory cases, including scanner failure versus a confirmed
  finding.
sources:
- osv
applies-when: The subject applies quality or security gates.
```

Required build, test, type, secret and selected security/architecture failures MUST affect the run
result. Severity and project thresholds are explicit; the library does not invent one universal
coverage percentage or suppress findings to obtain green. Secondary diagnostics retain a truthful
project-owned disposition. Retries are limited to established transient causes and never erase a
reproducible assertion failure or silently convert flaky behavior into an unconditional pass.

## R-0013 Architecture checks enforce actual boundaries

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.architecture]
criteria: A real forbidden dependency fails; a conforming fixture passes; a missing declared module is
  not green.
sources:
- import-linter
- dependency-cruiser
- archunit
applies-when: The project selects an architectural boundary check.
```

A selected architecture check MUST evaluate declared component responsibilities and dependency
constraints using suitable language-native or established analysis tools. It does not impose a
hexagonal folder skeleton on every script. Empty matched scopes cannot prove a declared boundary;
dynamic/framework entrypoints are considered when evaluating unused code. The result reports the
specific dependency/layer/cycle constraints evaluated, not general architecture perfection.

## R-0014 Documentation feedback follows executable sources

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.documents]
criteria: Check generated drift and broken examples while preserving honest limits for prose review.
sources:
- python-doctest
applies-when: The subject checks or updates implementation documentation.
```

Documentation checks MUST use canonical generation, executable examples and meaningful path/link
validation where these apply. Prose is kept aligned by the primary agent in the same engineering
change; an automated link or schema pass does not establish its truth. This library introduces no
mandatory prose digest, periodic attest ritual or automatic reviewer platform. An older adopted
standard's stronger claim rule is changed through an explicit compatible adoption process, not
silently disabled by this workflow. Artifact and provenance digests retain their separate purpose.

## R-0015 Untrusted checks do not inherit delivery authority

```item
strength: MUST
basis: owner
verification: review
criteria: Trace PR code, permissions, artifacts and secrets to each executed command and publication surface.
sources:
- gha-security
- gha-secrets
applies-when: The subject executes repository code or crosses CI/CD trust boundaries.
```

CI MUST separate untrusted source execution from deployment secrets, write authority and private
host state. Public fork PR code never gains access to the NDDev machine or deployment credentials.
Privileged event handlers do not execute candidate code, artifact scripts or attacker-supplied
commands before validating the actual trust boundary. Private repository visibility alone is not a
proof that every fork or workflow change is trusted. Only required permissions and secrets reach a
job; paid security functionality is not assumed from the fact that its CLI runs on a local machine.
