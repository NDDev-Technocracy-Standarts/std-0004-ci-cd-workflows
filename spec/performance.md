# Performance

## R-0016 Failures survive wrappers and shell pipelines

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.process]
criteria: Test setup failure, wrong interpreter, command quoting and a partially prepared replacement.
since: 0.1.0
applies-when: A wrapper or dependent operation executes commands.
```

An operation MUST preserve relevant process exit status and diagnostic context across wrappers,
pipelines and dependent steps. A failed download/setup cannot become successful installation because
a later shell exited zero. Replacement of a working tool or artifact follows successful preparation
of its replacement. Working directories, environment and tool lookup are consistent across setup,
build and verification; user-controlled text is passed as data where it is not intentionally a
trusted project command.

## R-0017 Optimization preserves obligations

```item
strength: MUST
basis: owner
verification: review
criteria: Compare required outputs and relevant queue/setup/execution costs before and after the optimization.
since: 0.1.0
sources:
- dora-feedback
applies-when: The subject changes execution efficiency or parallelism.
```

Optimization MUST preserve selected behaviors and trust boundaries. The implementation reduces
queue/setup duplication and the actual critical path, rather than maximize job count. Related small
checks may share a prepared job; independently useful heavy work may be parallelized within actual
CPU, memory and I/O limits. Shards have traceable inputs and aggregate completeness. New runner
features are used only where the deployed runner and tools support them. No benchmark speedup is
claimed from one warm sample or from removed coverage.

## R-0018 Caches have owners and bounded lifetimes

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.cache]
criteria: Check cache compatibility, simultaneous runners and pressure cleanup without losing active/recovery
  data.
since: 0.1.0
sources:
- cargo-config
- docker-cache
- cargo-cache
- sccache-local
- sccache-rust
applies-when: The subject reads, writes or reclaims acceleration state.
```

Caches MUST be acceleration state rather than proof of testing or the sole copy of release data.
Their keys and access boundaries account for relevant dependency, toolchain, platform and trust
inputs. Concurrent writers follow the backend's actual contract. Storage has bounded ownership and
reclamation that preserves active runs, releases and needed recovery artifacts. A broad destructive
cleanup of the shared host or cargo clean before every run is not the default optimization.

## R-0019 Reports remain useful without storage duplication

```item
strength: MUST
basis: owner
verification: partial
verified-by: [runtime.retention]
criteria: Inspect actual exported contents, mode preservation, retention and failure diagnostics.
since: 0.1.0
sources:
- gha-artifacts
applies-when: The subject exports or retains run diagnostics or artifacts.
```

Run diagnostics and artifacts MUST have an identified use, appropriate retention and safe contents.
GitHub logs/summaries serve small feedback; large artifacts are not duplicated merely to create a
report. Permissions, executable bits and hidden inputs needed by an actual package are preserved by
its packaging method. Credentials and private customer data never enter a public artifact, SBOM,
cache or log. A cancelled run's useful diagnostics remain identifiable without retaining its entire
workspace indefinitely.
