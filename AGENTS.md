# AGENTS.md

STD-0004 contains the public CI/CD standard and its OSS runtime. The package backs native composite
entrypoints. Keep implementation, selected fixture verification and real target acceptance distinct.
Native descriptors and manifests own exact edition and adoption identity. Read the
[package entry](src/nddev_cicd/README.md) and [local instructions](src/nddev_cicd/AGENTS.md)
for implementation responsibilities.

| Task | Canonical entry |
|---|---|
| Owner intent | [spec/intent.md](spec/intent.md) |
| Modules, routing and free execution | [spec/foundation.md](spec/foundation.md) |
| Source checks and quality | [spec/ci.md](spec/ci.md) |
| Performance and storage | [spec/performance.md](spec/performance.md) |
| Artifact and target behavior | [spec/delivery.md](spec/delivery.md) |
| Public usability and bounded pilot | [spec/maintenance.md](spec/maintenance.md) |
| Source evidence and verification limits | [spec/sources.yaml](spec/sources.yaml), [spec/verification.yaml](spec/verification.yaml) |

Use the prepared canonical `std0000 check`, `std0000 gen` and `nddev check`. Consult actual help;
these checks do not establish live CI/CD or semantic conformance. Implementations use existing
native tooling, not a second parser for the common standard format. Generated corpus/index/ledger
are compiler-owned and updated only by the canonical generator. No harness adapter is selected.

Public consumers must not need proprietary corpora or credentials. Keep account/browser/email
work outside this public repository. Project CI invokes ordinary native build/test commands.
