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
install_archive() {
  local url="$1" expected="$2" binary="$3" archive="$tools/$3.tar.gz" member
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$url" --output "$archive"
  printf '%s  %s\n' "$expected" "$archive" | sha256sum --check --status
  member="$(tar -tzf "$archive" | awk -F/ -v binary="$binary" '$NF == binary { print }')"
  [[ -n "$member" && "$member" != *$'\n'* ]]
  tar -xOzf "$archive" "$member" > "$tools/$binary"
  chmod 755 "$tools/$binary"
  rm "$archive"
}
install_archive 'https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz' \
  '8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8' actionlint
install_archive 'https://github.com/lycheeverse/lychee/releases/download/lychee-v0.24.2/lychee-x86_64-unknown-linux-musl.tar.gz' \
  '73657a111819a30c47c08352896796f23d64e4eb2b3ed39b6d32149241566fc5' lychee
"$tools/actionlint" --version
"$tools/lychee" --version
if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "$tools" >> "$GITHUB_PATH"; fi
