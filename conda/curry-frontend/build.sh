#!/bin/bash
# Installs the bundle of frontend/package.py --bundle-only, or the legacy
# pinned x86-64 PAKCS binary distribution used by the original build driver.
set -euo pipefail
if [ -f build-info.json ]; then
  cat build-info.json
  case "${target_platform:-$(uname -m)}" in
    linux-64|x86_64) expected=x86_64 ;;
    linux-aarch64|aarch64) expected=aarch64 ;;
    *) echo 'Unsupported front-end artifact target' >&2; exit 1 ;;
  esac
  grep -q '"architecture": "'"$expected"'"' build-info.json
  test "$(bin/curry-frontend --numeric-version)" = 2.0.0
  install -D -m 755 bin/curry-frontend "$PREFIX/bin/pakcs-frontend"
  cp licenses/LICENSE-PAKCS LICENSE
  cp licenses/LICENSE.curry-frontend LICENSE.curry-frontend
  if [ -f bin/libgmp.so.10 ]; then
    # Conda supplies GMP; do not install the wheel's vendored copy.
    patchelf --set-rpath '$ORIGIN/../lib' "$PREFIX/bin/pakcs-frontend"
  fi
else
  test "$(uname -m)" = x86_64
  install -D -m 755 bin/pakcs-frontend "$PREFIX/bin/pakcs-frontend"
fi
ln -s pakcs-frontend "$PREFIX/bin/curry-frontend"
