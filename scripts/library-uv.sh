#!/usr/bin/env bash
# Bootstrap only the callee's uv; never write caller PATH or shared-host packages.
set -euo pipefail
: "${RUNNER_TEMP:?Use an owned job temporary directory}"
case "$(uname -s):$(uname -m)" in
  Linux:x86_64) target=x86_64-unknown-linux-gnu; checksum=eadd9d27c134ab5ac1ffd4473b97a741407f3ea238288f03121fc4deddf90220 ;;
  Linux:aarch64) target=aarch64-unknown-linux-gnu; checksum=9041c73c99fdc5892cf128140beb354eca9231d502068cc36e6cb53a8e59ad14 ;;
  Darwin:arm64) target=aarch64-apple-darwin; checksum=cfe454573412ff7380d15fc7dae5997ab53ffce72fce0a78e91ddbc84001acd2 ;;
  Darwin:x86_64) target=x86_64-apple-darwin; checksum=bb7b805bdcf3d0bc8c74ceb94569e6b3e8aa35bd492acdbb9d46bf46d9d4ff6b ;;
  MINGW*:x86_64|MSYS*:x86_64) target=x86_64-pc-windows-msvc; checksum=3b2661a463a5baea7f5076ea2b25ab71d77f36a6c0d809e5350651792f80a672 ;;
  *) echo 'Unsupported library uv platform' >&2; exit 2 ;;
esac
extension=tar.gz
binary=uv
if [[ "$target" == *windows* ]]; then extension=zip; binary=uv.exe; fi
temporary_root="$RUNNER_TEMP"
if [[ "$target" == *windows* ]]; then temporary_root="$(cygpath -u "$RUNNER_TEMP")"; fi
stage="$(mktemp -d "$temporary_root/nddev-library-uv.XXXXXXXX")"
trap 'rm -rf "$stage"' EXIT
archive="$stage/uv.$extension"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  "https://github.com/astral-sh/uv/releases/download/0.13.1/uv-$target.$extension" --output "$archive"
if [[ "$target" == *apple* ]]; then
  observed="$(shasum -a 256 "$archive" | awk '{print $1}')"
else
  observed="$(sha256sum "$archive" | awk '{print $1}')"
fi
[[ "$observed" == "$checksum" ]]
if [[ "$extension" == zip ]]; then
  unzip -qq "$archive" "$binary" -d "$stage"
else
  tar -xOzf "$archive" "uv-$target/$binary" > "$stage/$binary"
fi
chmod 755 "$stage/$binary"
"$stage/$binary" --version >&2
rm "$archive"
printf '%s\n' "$stage/$binary"
trap - EXIT
