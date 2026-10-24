#!/bin/bash
# Builds the Curry front end 2.0.0 from the PAKCS 3.4.1 source on macOS and
# bundles it under frontend-work/bundle, as frontend.yml builds it on Linux
# aarch64: GHC 9.6.7 and Cabal through ghcup, the source patches of
# frontend/patches, GMP from Homebrew vendored beside the executable
# (frontend/package.py).  The CI job of ci.yml caches the bundle by the
# recipe that made it.  Requires Homebrew with gmp, curl and python3; writes
# the Haskell toolchain under $GHCUP_INSTALL_BASE_PREFIX (the home by
# default).  Issue #162.
set -euo pipefail
: "${GHC_VERSION:=9.6.7}"
: "${CABAL_VERSION:=3.10.3.0}"
: "${FRONTEND_SOURCE_URL:=https://www.curry-lang.org/pakcs/download/pakcs-3.4.1-src.tar.gz}"
: "${FRONTEND_SOURCE_SHA256:=71e8030e2efb2295c5862e0c09c9ea2497cfc3b971d8903ce40df66d25e47c22}"
export GHCUP_INSTALL_BASE_PREFIX="${GHCUP_INSTALL_BASE_PREFIX:-$HOME}"
export BOOTSTRAP_HASKELL_NONINTERACTIVE=1 BOOTSTRAP_HASKELL_MINIMAL=1 BOOTSTRAP_HASKELL_ADJUST_BASHRC=0
export LC_ALL=C.UTF-8
test "$(uname -s)" = Darwin || { echo "this script builds the front end on macOS" >&2; exit 2; }
mkdir -p frontend-work/logs
exec > >(tee frontend-work/logs/frontend-macos.log) 2>&1
set -x
uname -a
sw_vers
xcode-select -p
python3 --version
brew --prefix gmp
export PATH="$GHCUP_INSTALL_BASE_PREFIX/.ghcup/bin:$PATH"
if ! command -v ghcup >/dev/null; then
  curl --fail --location --retry 3 https://get-ghcup.haskell.org \
    --output frontend-work/ghcup-bootstrap.sh
  shasum -a 256 frontend-work/ghcup-bootstrap.sh
  bash frontend-work/ghcup-bootstrap.sh
fi
ghcup --version
ghcup install ghc "$GHC_VERSION"
ghcup set ghc "$GHC_VERSION"
ghcup install cabal "$CABAL_VERSION"
ghcup set cabal "$CABAL_VERSION"
test "$(ghc --numeric-version)" = "$GHC_VERSION"
test "$(cabal --numeric-version)" = "$CABAL_VERSION"
python3 frontend/fetch.py --output frontend-work/fetch \
  --url "$FRONTEND_SOURCE_URL" --sha256 "$FRONTEND_SOURCE_SHA256"
bash frontend/build.sh frontend-work/fetch/source frontend-work/build
rm -rf frontend-work/bundle
python3 frontend/package.py --binary frontend-work/build/curry-frontend \
  --licenses frontend-work/fetch/licenses --bundle-only --output frontend-work/bundle
test "$(frontend-work/bundle/bin/curry-frontend --numeric-version)" = 2.0.0
otool -L frontend-work/bundle/bin/curry-frontend
cat frontend-work/bundle/build-info.json
