# Native library, authoring and selected fixture entrypoints; discovery applies nothing.
set minimum-version := "1.55.0"
set shell := ["bash", "--norc", "-euo", "pipefail", "-c"]
set positional-arguments
set default-list
set lazy
set dotenv-load := false
compiler := env("NDDEV_AUTHORING_COMPILER", "std0000")

# Prepare the locked contributor environment without selecting a target.
[group("setup")]
setup:
    uv sync --locked

# Inspect repository structure with the separately provisioned STD-0001 validator.
[group("check")]
check *args:
    if [ "${1:-}" = -- ]; then shift; fi; nddev check "$@"

# Run Python regressions; optional arguments retain native pytest meaning.
[group("check")]
test *args:
    if [ "${1:-}" = -- ]; then shift; fi; uv run --locked pytest "$@"

# Run the selected real SDK fixture and controlled failure; requires that SDK and native tools.
[group("check")]
native profile *args:
    if [ "${1:-}" = -- ]; then shift; fi; uv run --locked python tests/run_native.py "$@"

# Check Python rules without rewriting source.
[group("check")]
lint:
    uv run --locked ruff check .

# Check the configured native Python type boundary.
[group("check")]
types:
    uv run --locked basedpyright

# Check owned Python and just source formatting.
[group("check")]
format-check: just-check
    uv run --locked ruff format --check src tests

# Parse/format-check the sole owned just source without changing it.
[group("check")]
just-check:
    {{ quote(just_executable()) }} --justfile {{ quote(justfile()) }} --fmt --check

# Rewrite only Python and just source formatting.
[group("write")]
fmt:
    uv run --locked ruff format src tests
    {{ quote(just_executable()) }} --justfile {{ quote(justfile()) }} --fmt

# Check the real routing documentation example.
[group("check")]
doctest:
    uv run --locked python -m doctest docs/examples.md

# Inspect the real public/private routing example without allocating a job.
[group("example")]
routing:
    uv run --locked python examples/routing.py

# Check the package-owned generated profile reference.
[group("check")]
reference-check:
    uv run --locked python -m nddev_cicd reference --check

# Regenerate only the package-owned profile reference with its actual producer.
[group("write")]
reference-gen:
    uv run --locked python -m nddev_cicd reference

# Verify exact native facade/backend runtime bindings.
[group("check")]
runtime-binding:
    uv run --locked python scripts/check-runtime-lock.py

# Check the canonical normative corpus with the separately prepared compiler.
[group("check")]
authoring-check *args:
    if [ "${1:-}" = -- ]; then shift; fi; {{ quote(compiler) }} check "$@"

# Regenerate compiler-owned normative outputs explicitly.
[group("write")]
authoring-gen *args:
    if [ "${1:-}" = -- ]; then shift; fi; {{ quote(compiler) }} gen "$@"

# Build the public Python wheel/source distribution through the selected backend.
[group("build")]
package *args:
    if [ "${1:-}" = -- ]; then shift; fi; uv build "$@"

# Preserve the native library CLI and all its explicit source/artifact/target semantics.
[group("native")]
library *args:
    if [ "${1:-}" = -- ]; then shift; fi; uv run --locked python -m nddev_cicd "$@"

# Full source feedback; selected SDK and remote-target acceptance remain separate.
[group("check")]
verify: check format-check lint types test doctest reference-check runtime-binding authoring-check
