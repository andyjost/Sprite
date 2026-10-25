#!/bin/bash
# Build a fetched source with the runner's Haskell toolchain. No fetch here
# except Cabal/Stack's dependency resolution; fetch.py owns the source.
set -euxo pipefail
source_dir=$(cd "$1" && pwd -P)
mkdir -p "$2"
output_dir=$(cd "$2" && pwd -P)
scripts_dir=$(cd "$(dirname "$0")" && pwd)
os=$(uname -s)
arch=$(uname -m)
# macOS has shasum, not sha256sum, unless GNU coreutils is installed.
sha256() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
# The linkage of a binary: the ELF program headers and the dynamic section
# on Linux, the load commands on macOS (issue #162).
describe_binary() {
  if [ "$os" = Darwin ]; then
    otool -L "$1"
    otool -l "$1" | grep -A 4 -E 'LC_BUILD_VERSION|LC_VERSION_MIN_MACOSX|LC_RPATH|LC_LOAD_DYLIB|LC_ID_DYLIB' || true
  else
    readelf -l -d "$1"
  fi
}
ghc --version
ghc --info
cabal --version
if [ "$os" != Darwin ] && [ "$arch" = x86_64 ]; then
  stack --version
fi
gcc --version
if [ "$os" = Darwin ]; then
  ld -v
else
  ld --version
  ldd --version
fi
cd "$source_dir"
for patchfile in "$scripts_dir"/patches/*.patch; do
  [ -f "$patchfile" ] || continue
  sha256 "$patchfile"
  patch --batch --forward --fuzz=0 -p1 < "$patchfile"
done
cat ./*.cabal
[ ! -f stack.yaml ] || cat stack.yaml
executable=$(python3 - <<'PY'
from pathlib import Path
import re
names = [name for path in Path('.').glob('*.cabal')
    for name in re.findall(r'^executable\s+(\S+)', path.read_text(), re.M | re.I)]
preferred = [n for n in names if n in ('curry-frontend', 'pakcs-frontend')]
if len(preferred) == 1:
  print(preferred[0])
elif len(names) == 1:
  print(names[0])
else:
  raise SystemExit('Reviewer must identify executable: ' + repr(names))
PY
)
build_frontend() {
  local options='-v'
  # GMP from Homebrew on macOS: GHC links the bignum library against it.
  local extra=''
  if [ "$os" = Darwin ] && command -v brew >/dev/null 2>&1 && brew --prefix gmp >/dev/null 2>&1; then
    local gmp
    gmp=$(brew --prefix gmp)
    extra="--extra-lib-dirs=$gmp/lib --extra-include-dirs=$gmp/include"
  fi
  if [ "$os" != Darwin ] && [ "$arch" = x86_64 ]; then
    # Do not override the source resolver with a modern snapshot.
    python3 - <<'PY'
from pathlib import Path
import re
text = Path('stack.yaml').read_text()
if not re.search(r'^resolver:\s*[\x27\x22]?lts-16\.9[\x27\x22]?\s*(?:#.*)?$', text, re.M):
  raise SystemExit('Unexpected resolver; reviewer must inspect stack.yaml.')
PY
    [ "$?" = 0 ] || return 1
    stack --system-ghc --no-install-ghc build --verbose \
      --copy-bins --local-bin-path "$output_dir/installed" --ghc-options="$options" || return $?
    cp "$output_dir/installed/$executable" "$output_dir/curry-frontend" || return $?
  else
    # Start at GHC 9.6; retain solver/compile errors for named source fixes.
    # shellcheck disable=SC2086
    cabal build "exe:$executable" --verbose=3 --allow-newer $extra \
      --ghc-options="$options" || return $?
    local built_binary
    # The same solver flags as the build: list-bin plans again.
    # shellcheck disable=SC2086
    built_binary=$(cabal list-bin "exe:$executable" --allow-newer $extra \
      --ghc-options="$options") || return $?
    cp "$built_binary" "$output_dir/curry-frontend" || return $?
  fi
  describe_binary "$output_dir/curry-frontend" > "$output_dir/dynamic-elf.txt" || return $?
  cat "$output_dir/dynamic-elf.txt"
}
if [ "$os" = Darwin ] || [ "$arch" != x86_64 ]; then
  cabal update --verbose=3
fi
# CI run 3 established that AlmaLinux 8 has no GMP archive. Use its shared
# GMP and glibc; package.py vendors GMP with $ORIGIN and verifies the ELF floor.
build_frontend 2>&1 | tee "$output_dir/dynamic.log"
echo dynamic > "$output_dir/linkage-requested.txt"
test "$("$output_dir/curry-frontend" --numeric-version)" = 2.0.0
"$output_dir/curry-frontend" --version
file "$output_dir/curry-frontend"
if [ "$os" = Darwin ]; then
  describe_binary "$output_dir/curry-frontend" > "$output_dir/elf.txt"
else
  readelf -d -V "$output_dir/curry-frontend" > "$output_dir/elf.txt"
fi
cat "$output_dir/elf.txt"
ghc-pkg list > "$output_dir/ghc-packages.txt"
find . -name plan.json -exec cp '{}' "$output_dir/plan.json" \;
