# Delivery

## R-0020 CD consumes an eligible integrated result

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.lineage]
criteria: Exercise late base changes, superseded PR results and malicious/unrelated artifact references.
sources:
- gha-events
applies-when: The subject determines eligibility for deployment.
```

Deployment MUST consume an authorized, integrated candidate whose applicable PR checks succeeded.
The artifact is bound to the actual intended source/configuration, not selected by a mutable latest
name or an unrelated successful run. A merge accepted by an API is not a finished deployment. If the
final integrated source differs materially from the tested candidate, eligibility is established
through the project's existing corresponding check path rather than assumed from tree/branch names.

## R-0021 Artifact promotion preserves identity

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.artifact, runtime.release, runtime.oci]
criteria: Trace artifact bytes from trusted build through download and target installation.
sources:
- slsa
applies-when: A build artifact is produced, published or promoted.
```

A supplied release artifact MUST identify its source, build inputs and digest. The same verified
artifact is promoted between compatible environments where possible, with environment configuration
kept separate. Necessary environment-specific rebuilds create a new artifact identity and receive
applicable build validation, not a copied success label. Provenance/attestation claims reflect the
actual build and provider guarantees; a checksum alone neither authenticates an artifact nor grants
SLSA level certification.

## R-0022 Native deployment is complete rather than declarative only

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.delivery, runtime.preflight, runtime.current, runtime.remote]
criteria: Run an adapter against an authorized representative target; a generated plan is not an applied
  result.
sources:
- gha-secrets
- android-apkanalyzer
- android-bundletool
applies-when: The project selects a deployment adapter.
```

A delivered CD module MUST invoke the project's actual configured deployment path and observe its
outcome. First-party adapters remain modular and cover their documented target types without forcing
one universal plan/approval platform. Repository secrets provide required credentials through
supported host features; private GitHub Free is not assumed to have organization secrets or
Environments. Source-only projects and mobile artifacts without store credentials have their real
completion boundary; a fictitious production service is not required.

## R-0023 The target serializes deployment

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.target-lock, runtime.remote]
criteria: Test overlapping attempts to one target, separate targets, and stale attempts after newer delivery.
sources:
- gha-concurrency
applies-when: The subject can mutate a shared delivery target.
```

Concurrent changes to the same delivery target MUST have one effective coordination owner. A unique
attempt/deployment ID is not a target lock. Repository-local concurrency is not a cross-repository
lock. An older attempt cannot overwrite a newer accepted target state, and superseding CI cancellation
is not blindly applied to a running data migration. Read-only or unrelated jobs need not share the
mutation lock. Native target/infrastructure primitives are preferred over a new scheduling service.

## R-0024 Recovery respects data and partial state

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.recovery]
criteria: Cover failed health checks, interruption after migration and an incompatible previous artifact.
applies-when: Delivery changes data or encounters partial execution or failure.
```

Failed or interrupted delivery MUST leave enough truthful state to diagnose and resume or recover
through the existing target mechanism. Data-affecting operations use an appropriate existing backup
or recoverable transition unless the user explicitly waived it for that scope. No-backup authority
is not permission for unrelated deletion. A previous binary is not automatically compatible with
migrated data. Recovery does not silently cancel other agents' work or retry uncertain mutations
before reconciling their actual result.

## R-0025 Acceptance identifies the running result

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.health]
criteria: Correlate target version, actual scenario, timing and logs, including a deliberately failed
  scenario.
applies-when: The invocation claims a delivered result.
```

Successful delivery MUST identify the intended target revision and demonstrate the relevant health
or user scenario with available current diagnostics. A process start or absence of log lines alone
is insufficient when the intended scenario fails. Active DAST, stress and destructive fixtures use
authorized suitable test targets, not live customer data by default. Failure remains visible to the
owning GitHub task; no pipeline auto-closes a delivery parent merely at merge.
