# Maintenance

## R-0026 The library is usable outside its publisher account

```item
strength: MUST
basis: owner
verification: review
criteria: Use a caller outside the publisher organization and inspect runtime dependency/access requirements.
applies-when: The library exposes public technical entrypoints.
```

Public technical entrypoints MUST be usable by eligible public and private consumers without reading
proprietary NDDev standards, obtaining a paid plan or copying private manifests. NDDev's own adoption
and catalog rules still apply to its projects. Platform routing is carried by supported consumer
configuration, and public examples contain no real infrastructure identifiers or unprovided secrets.
Build and packaging commands remain runnable through their native project interfaces.

## R-0027 Claims of support match real verification

```item
strength: MUST
basis: owner
verification: review
criteria: Compare each advertised capability against an actual result and its named limits.
sources: [archived-native-fixtures, archived-fuzz-fixtures]
applies-when: The implementation declares capabilities or verification coverage.
```

The implementation MUST distinguish implemented, verified, unsupported and unavailable capabilities.
A profile's success is supported by executed native fixtures and actual caller behavior appropriate
to its claims, not only parsed YAML or a command-recording double. A declared pilot
covers its real adopters; language/CD fixtures cover additional selected modules without fabricated
business deployments. Unexecuted platform or hardware scenarios remain explicitly unverified.

## R-0028 Adoption and cleanup have a finite scope

```item
strength: MUST
basis: owner
verification: review
criteria: Check pilot boundaries, references, retained previous consumers and cleanup of replaced active
  paths.
applies-when: The task adopts or replaces workflows or related integrations.
```

Adoption MUST preserve existing consumers and issued identities until an explicit transition replaces
them. Each rollout has an explicit project and infrastructure scope; successful catalog registration or
a pilot does not authorize a fleet-wide migration. Obsolete task-created workflows, settings, dead code and duplicated instructions
are removed after the replacement works. Valid unrelated backlog and historical evidence remain.
The task finishes after the agreed implementation, pilot and integration; new audit services, quotas
of reruns and fleet-wide migrations are not added to manufacture certainty.
