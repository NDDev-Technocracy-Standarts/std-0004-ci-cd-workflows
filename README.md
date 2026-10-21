# NDDev CI/CD Workflows

A public OSS library for thin GitHub workflows, native source checks and delivery of the exact tested
artifact. Maintainers select applicable profiles and retain their existing build tools, runners and
targets. Public consumers need no private NDDev compiler, corpus or credentials.

![Admission precedes native source checks and exact artifact delivery to an existing target](docs/architecture.svg)

## Try runner selection

From this checkout, prepare the locked environment and inspect the real public routes:

```sh
uv sync
uv run python examples/routing.py
```

The example reads the library's native runner labels without allocating jobs. Public Linux and Windows use x64; macOS uses ARM64. All use standard GitHub-hosted runners. Private Linux uses existing caller-owned self-hosted
capacity; private Windows/macOS require compatible confirmed no-overage admission. The
[consumer guide](docs/usage.md) explains the distinct public and private calling paths.

## Source, artifact, target

For private vulnerability reports, use the [security reporting channel](SECURITY.md).

The [CI composite](.github/actions/ci/action.yml) executes profiles selected by the caller's native
contract. A short PR gate permits merge; full main CI establishes production readiness. Affected
components include changes from any superseded or failed main validation. The [admission composite](.github/actions/admit/action.yml) resolves capacity before job
allocation. The [delivery composite](.github/actions/deliver/action.yml) consumes the artifact from
successful full main CI, verifies lineage and tested-tree identity, and coordinates an
existing target. Delivery promotes that artifact without rebuilding it. Each callee resolves its own package separately from
the caller checkout. The [impact planner](.github/actions/impact/action.yml) exposes component selection
before dependent jobs allocate capacity. The [failure publisher](.github/actions/feedback/action.yml)
returns bounded native run feedback to an owning Issue without executing candidate code.

[The package README](src/nddev_cicd/README.md) explains ownership, recovery and native-tool boundaries.
The [generated profile reference](docs/profiles.md) summarizes selectable operations and points to
native command definitions. Optional public security, release preparation, OCI and bounded advanced
operations use the same implementation and explicit applicability.
The [optional native quality modules](docs/usage.md#ready-bounded-advanced-operations) add mutation,
benchmark, source-host assessment and disposable-executor fuzzing feedback without selecting them
for existing consumers.

## Check and maintain

Run `uv run pytest` for runtime regressions, `uv run python -m doctest docs/examples.md` for the
selected routing example, and `uv run python -m nddev_cicd reference --check` for owned reference drift.
[AGENTS.md](AGENTS.md) routes normative changes to the canonical source and implementation changes to
local checks. Ordinary documentation remains directly editable.

Native fixture drivers exercise selected SDKs and failure paths. Source workflows include public
Linux, Windows and Apple runners. Remote delivery fixtures use isolated targets and actual SSH/SCP;
main completion smoke checks artifact lineage and recovery. These checks do not establish every
SDK combination, a production deployment, or acceptance on a physical remote server.

The [normative descriptor](standard.yml), [consumer guide](docs/usage.md),
[executable example](docs/examples.md), and [origins](docs/origins.md) provide detailed navigation.
[GitHub Releases](https://github.com/NDDev-Technocracy-Standarts/std-0004-ci-cd-workflows/releases)
is the canonical journal. The source uses [AGPL-3.0-only](LICENSE); imported grants remain intact.

## Native command interface

The project adopts draft STD-0006 0.1.0 from its
[selected immutable source](https://github.com/NDDev-Technocracy-Standarts/std-0006-project-command-interface/blob/9a70ac36e986cc8328c995d7428c45f4d13f7868/standard.yml).
Bare `just` lists applicable operations without installing SDKs or reading credentials.
`just setup` prepares locked contributor dependencies; `just verify` checks repository structure,
Python source, routing documentation, profile-reference drift, exact runtime bindings and the
normative corpus. The structure validator and authoring compiler are separately provisioned;
missing required tools remain explicit failures. `just native PROFILE` selects one real SDK fixture,
including its invalid-source case, and requires that profile's SDK and native tools.

Formatting, profile-reference generation, corpus generation and packaging have separate recipes.
`just library -- --help` preserves the actual CLI; source, artifact and target operations retain
its validation, credentials and recovery boundaries. There is no application development server.
The Bash interface is accepted on Linux; public Windows and Apple workflows continue using their
native entrypoints and do not acquire acceptance from a Linux command-source check. CI retains
its short PR and full main/target phases and can invoke the same owning native tools directly.
