# Measured speed practices

Non-normative guidance for R-0017 (optimization preserves obligations), R-0018 (owned caches),
R-0007 and R-0020 (gates and admission). Each practice names what it removes from the critical
path and the obligation it keeps. The numbers come from one adopting project's private
self-hosted runners and existing hosts (28–29 Oct 2026). They show the order of magnitude, not a
benchmark (R-0017: no speedup from one warm sample).

## Find the critical path first

Read the job and step timestamps of real runs before changing anything: queue time, `Set up
job`, checkout and the work itself. In the measured project the work took 20–120 s while
checkout took 150–630 s and `Set up job` up to 126 s. Optimizing the tests would have changed
nothing.

## Promotion

- **Fast-forward main to the verified dev commit** (STD-0003 R-0015) instead of a promotion pull
  request with its own gate and merge commit. The production candidate is then the exact commit
  dev verified, and full main validation still runs on its push (R-0020). Measured: promotion of
  seven repositories went from 5.3 min (25–50 min while promotion PRs ran the full gate) to
  seconds. Prerequisite: every main is an ancestor of dev. Fast-forward dev to main once when
  main is only promotion merges ahead with equal trees. A main holding work dev lacks (a hotfix)
  refuses until that work is merged into dev (STD-0003 R-0014).
- **Promote side by side.** Independent repositories advance in parallel and the aggregate
  (superproject) advances last, so one module's failure keeps the composition off main.
- **Retry runner faults once, not changes.** Rerun only the failed jobs of a first attempt, as
  native admission does, then let a repeated failure stand. Measured causes: a checkout that died
  mid-fetch, a toolchain that vanished from a shared SDK, a run cancelled from outside. Never
  cancel a validation run of a SHA that a later gate will read: the cancelled aggregate becomes
  that SHA's latest result.

## Checkout

- **Fetch only what the job reads.** A sparse checkout without a filter still downloads every
  blob of the tree. A cone sparse checkout of a few files plus `filter: blob:none` fetched in
  3–4 s, where the full tree (558 MB of store exports) took 150–600 s.
- **Mind what `blob:none` defers.** The checkout then fetches every blob of the sparse set on
  demand, as a second request. On one set of runners that request ran at a fraction of the normal
  rate: 16 MB took 15–18 min, while single-pack fetches on the same runners took 2–3 s. When a
  few large files are the problem, `blob:limit=<size>` brings every smaller blob in the one fetch
  (54 MB instead of 264 MB in the measured repository). Excluding the larger files from the
  sparse set then leaves the checkout nothing to fetch. Time the checkout step, not only the
  fetch.
- **A history scanner needs history, not a working tree.** A secret scan with `fetch-depth: 0`,
  `filter: blob:none` and a sparse checkout of the configuration files went from 294–350 s to
  about 40 s. Partial clones fetch missing blobs on demand, so a later step that widens the
  sparse set needs the read token in its own environment. With `persist-credentials: false` it
  is not in `.git/config`.
- **Check through the API instead of checking out.** A gate that only compares ancestry and trees
  reads `compare` and `git/commits` with `contents: read`. A `pull_request` run's `github.sha` is
  GitHub's test merge, so no pulls API call (which needs `pull-requests: read`) is required.
- On persistent runners a sparse setting can outlive its job. Use a checkout implementation that
  resets it, or a fresh workspace per job.

## Runner setup

- **Cache action archives on self-hosted runners.** The runner reads
  `ACTIONS_RUNNER_ACTION_ARCHIVE_CACHE` (`{owner}_{repo}/{sha}.tar.gz`) before downloading an
  action, which removes the per-job action downloads from `Set up job`. Keep the archives keyed by
  the pinned SHAs.
- **Keep git objects near the runner.** A bare mirror per repository on runner storage, used via
  `--reference`/alternates, turns a full fetch into a fetch of the new objects (STD-0011 owns the
  shared cache).

## Images

- **Key images by their inputs, not by the commit.** Digest the build specification, the
  Dockerfile, the `.dockerignore` and the Git object of each path the target's stages copy or
  bind-mount. An image whose inputs did not change keeps its tag and digest. Its containers are
  then not replaced, and a docs or workflow change rebuilds nothing. Treat anything the parser
  cannot resolve as the whole context, which costs a rebuild, never a stale image. A
  whole-context image may still leave out the plain names its `.dockerignore` excludes.
- **Ask the registry once per image, all at once.** One manifest-and-config inspection per image,
  issued in parallel, took 4 s where two sequential round trips per image took 95 s.
- For layers that do rebuild, export `mode=max` registry cache per target (inline cache supports
  only `min`).

## Activation on existing hosts

- **Replace only what changed.** Record each service's selected configuration digest and
  container after activation, and replace a service only when either differs. Compose's own
  `config-hash` label may disagree with `config --hash` for some services, so compare against
  the record. The first release on a host replaces everything once. When a service is replaced,
  log which configuration field names changed. Never log values, because the configuration
  carries environment secrets.
- **Settle only for what was replaced.** A fixed telemetry settle (90 s) is needed only after a
  runtime restarted. A release that replaced nothing waits a few seconds.
- **Reuse an identical recovery archive.** When the previous release archived exactly the same
  image references, hard-link its archive and verify its recorded digest instead of saving the
  images again (30 s).
- **Reload instead of waiting out a resolver cache.** A proxy that resolves upstream names at
  run time (nginx with `resolver ... valid=10s`) keeps each worker's cached address. A reload
  starts workers that resolve afresh, and the old ones stop accepting connections. Wait for the
  new worker generation (about 0.5 s) instead of the cache lifetime: a rolling replacement
  dropped two 12 s waits.
- **Poll readiness yourself or set `start_interval`.** A deploy that waits on Docker's health
  status is bounded by the health `interval` (often 30 s). Running the health command directly
  every 1–2 s, or `start_interval` (recent Docker Engine and Compose), makes readiness visible at
  once.
- **Bind directories, not single configuration files.** A single-file bind keeps the inode the
  container was created with. A checkout that replaces the file then leaves reloads reading the
  old configuration.

## Sources

- [Ken Muse: runner images with an action archive cache](https://www.kenmuse.com/blog/building-github-actions-runner-images-with-an-action-archive-cache/)
- [Depot: why organizations have slow actions/checkout](https://depot.dev/blog/why-organizations-have-slow-actions-checkout)
- [actions/checkout reference cache proposal (ADR 2303)](https://git.libre-chip.org/actions/checkout/src/commit/090955f4b7c3c5e5b3f067c16ffb4d193e386e18/adrs/2303-reference-cache.md)
- [Docker: cache storage backends](https://docs.docker.com/build/cache/backends/)
- [Docker Compose healthcheck `start_interval`](https://docs.docker.com/reference/compose-file/services/#healthcheck)
