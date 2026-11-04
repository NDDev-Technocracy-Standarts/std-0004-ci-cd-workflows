#!/usr/bin/env bash
# Job-local native tools for this repository's Linux CI; no shared-host packages.
set -euo pipefail
: "${RUNNER_TEMP:?Use an owned job-local temporary directory}"
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]]
tools="$RUNNER_TEMP/nddev-native-tools"
if [[ -e "$tools" && ! -f "$tools/.nddev-tools-owner" ]]; then
  echo 'Refusing an unowned native-tool directory' >&2
  exit 2
fi
mkdir -p "$tools"
printf 'std-0004-ci-tools/v1\n' > "$tools/.nddev-tools-owner"
# A full timeout must discard both origin and CDN connection caches before retrying.
# curl retains ownership of transient HTTP classification; digest checks stay below.
download() {
  local attempt status=28 deadline=$((SECONDS + 480)) remaining limit
  for attempt in 0 1 2 3; do
    remaining=$((deadline - SECONDS))
    if (( remaining <= 0 )); then return "$status"; fi
    limit=120
    if (( remaining < limit )); then limit="$remaining"; fi
    if curl --retry 3 --retry-max-time "$limit" --connect-timeout 20 --max-time "$limit" \
      --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$@"; then
      return 0
    else
      status=$?
    fi
    if [[ "$status" != 28 || "$attempt" == 3 ]]; then return "$status"; fi
  done
  return "$status"
}
# shellcheck source=scripts/prepared-artifact.sh
source "$(dirname "${BASH_SOURCE[0]}")/prepared-artifact.sh"
verified_download() {
  local url="$1" expected="$2" destination="$3" status
  if nddev_prepared_artifact "$expected" "$destination"; then return 0; else status=$?; fi
  if [[ "$status" != 1 ]]; then return "$status"; fi
  download "$url" --output "$destination"
}
install_archive() {
  local url="$1" expected="$2" binary="$3" archive="$tools/$3.tar.gz" member
  if [[ -f "$tools/$binary.source" && "$(cat "$tools/$binary.source")" == "$expected" ]] && \
    (cd "$tools" && sha256sum --check --status "$binary.sha256"); then
    return
  fi
  verified_download "$url" "$expected" "$archive"
  printf '%s  %s\n' "$expected" "$archive" | sha256sum --check --status
  member="$(tar -tzf "$archive" | awk -F/ -v binary="$binary" '$NF == binary { print }')"
  [[ -n "$member" && "$member" != *$'\n'* ]]
  tar -xOzf "$archive" "$member" > "$tools/$binary.new"
  chmod 755 "$tools/$binary.new"
  mv "$tools/$binary.new" "$tools/$binary"
  rm "$archive"
  printf '%s\n' "$expected" > "$tools/$binary.source"
  (cd "$tools" && sha256sum "$binary" > "$binary.sha256")
}
# Downloads come from the lock generated from the technology registry, or from the caller's lock.
tools_lock="${NDDEV_TOOLS_LOCK:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.github/tools.lock.json}"
locked() {
  python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["tools"][sys.argv[2]][sys.argv[3]])' \
    "$tools_lock" "$1" "$2"
}
install_locked() {
  local name="$1" kind
  kind="$(locked "$name" kind)"
  case "$kind" in
    archive) install_archive "$(locked "$name" url)" "$(locked "$name" sha256)" "$name" ;;
    file) install_file "$(locked "$name" url)" "$(locked "$name" sha256)" "$name" ;;
    *) echo "Unknown locked tool kind for $name" >&2; exit 2 ;;
  esac
}
install_file() {
  local url="$1" expected="$2" binary="$3"
  if [[ -f "$tools/$binary" ]] && printf '%s  %s\n' "$expected" "$tools/$binary" | sha256sum --check --status; then
    return
  fi
  verified_download "$url" "$expected" "$tools/$binary.new"
  printf '%s  %s\n' "$expected" "$tools/$binary.new" | sha256sum --check --status
  chmod 755 "$tools/$binary.new"
  mv "$tools/$binary.new" "$tools/$binary"
}
capabilities="${*//,/ }"
unique=''
for capability in $capabilities; do
  case "$capability" in rust|security|quality|compiler|shell|container|infrastructure|workflows|documentation) ;; *) echo 'Unknown tool capability' >&2; exit 2 ;; esac
  case " $unique " in *" $capability "*) ;; *) unique+=" $capability" ;; esac
done
install_locked actionlint
install_locked lychee
install_locked zizmor
for capability in $unique; do
if [[ "$capability" == rust || "$capability" == quality ]]; then
  install_locked cargo-machete
fi
if [[ "$capability" == compiler ]]; then
  install_locked ccache
  "$tools/ccache" --version
fi
if [[ "$capability" == quality ]]; then
  install_locked typos
  "$tools/typos" --version
  "$tools/cargo-machete" --version
  library="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  library_uv="$(bash "$library/scripts/library-uv.sh")"
  quality_runtime="$(UV_PROJECT_ENVIRONMENT="$tools/quality-runtime" UV_CACHE_DIR="${NDDEV_UV_CACHE_ROOT:-$tools/quality-downloads}" \
    bash "$library/scripts/prepare-python-tool-runtime.sh" "$library_uv" "$library/.github/native-tools" --group quality)"
  SEMGREP_APP_TOKEN='' SEMGREP_SEND_METRICS=off SEMGREP_ENABLE_VERSION_CHECK=0 OTEL_SDK_DISABLED=true \
    SEMGREP_SETTINGS_FILE="$tools/quality-semgrep-settings.yml" "$quality_runtime/bin/semgrep" --version
  if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "$quality_runtime/bin" >> "$GITHUB_PATH"; fi
fi
if [[ "$capability" == rust ]]; then
  install_locked cargo-deny
  install_locked sccache
  install_locked cargo-audit
  install_locked cargo-nextest
  "$tools/cargo-deny" --version
  "$tools/sccache" --version
  "$tools/cargo-audit" --version
  "$tools/cargo-nextest" --version
fi
if [[ "$capability" == security ]]; then
  install_locked gitleaks
  "$tools/gitleaks" version
  install_locked osv-scanner
  "$tools/osv-scanner" --version
  install_locked trufflehog
  "$tools/trufflehog" --version
  library="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  library_uv="$(bash "$library/scripts/library-uv.sh")"
  security_runtime="$(UV_PROJECT_ENVIRONMENT="$tools/security-runtime" UV_CACHE_DIR="${NDDEV_UV_CACHE_ROOT:-$tools/security-downloads}" \
    bash "$library/scripts/prepare-python-tool-runtime.sh" "$library_uv" "$library/tools/security" --no-dev)"
  "$security_runtime/bin/bandit" --version
  if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "$security_runtime/bin" >> "$GITHUB_PATH"; fi
fi
if [[ "$capability" == shell ]]; then
  install_locked shellcheck
  archive="$tools/bats.tar.gz"
  bats_sha="$(locked bats-core sha256)"
  verified_download "$(locked bats-core url)" "$bats_sha" "$archive"
  printf '%s  %s\n' "$bats_sha" "$archive" | sha256sum --check --status
  mkdir -p "$tools/bats-sdk"
  tar -xzf "$archive" --strip-components=1 --directory "$tools/bats-sdk"
  rm "$archive"
  "$tools/bats-sdk/bin/bats" --version
  if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "$tools/bats-sdk/bin" >> "$GITHUB_PATH"; fi
fi
if [[ "$capability" == container || "$capability" == infrastructure ]]; then
  install_locked trivy
  "$tools/trivy" --version
fi
if [[ "$capability" == container ]]; then
  install_locked hadolint
  "$tools/hadolint" --version
fi
done
"$tools/actionlint" --version
"$tools/lychee" --version
if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "$tools" >> "$GITHUB_PATH"; fi
