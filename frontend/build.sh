#!/bin/bash
# Build a fetched source with the runner's Haskell toolchain. No fetch here
# except Cabal/Stack's dependency resolution; fetch.py owns the source.
set -euxo pipefail
source_dir=$(realpath "$1")
output_dir=$(realpath -m "$2")
scripts_dir=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$output_dir"
ghc --version
ghc --info
cabal --version
if [ "$(uname -m)" = x86_64 ]; then
  stack --version
fi
gcc --version
ld --version
ldd --version
cd "$source_dir"
for patchfile in "$scripts_dir"/patches/*.patch; do
  [ -f "$patchfile" ] || continue
  sha256sum "$patchfile"
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
  local linkage=$1
  local options='-v'
  local static_args=()
  if [ "$linkage" = static ]; then
    options+=' -static -optl-static -optl-pthread'
  fi
  if [ "$(uname -m)" = x86_64 ]; then
    # Do not override the source resolver with a modern snapshot.
    python3 - <<'PY'
from pathlib import Path
import re
text = Path('stack.yaml').read_text()
if not re.search(r'^resolver:\s*[\x27\x22]?lts-16\.9[\x27\x22]?\s*(?:#.*)?$', text, re.M):
  raise SystemExit('Unexpected resolver; reviewer must inspect stack.yaml.')
PY
    [ "$?" = 0 ] || return 1
    if [ "$linkage" = static ]; then
      static_args=(--no-shared)
    fi
    stack --system-ghc --no-install-ghc build --verbose "${static_args[@]}" \
      --copy-bins --local-bin-path "$output_dir/installed" --ghc-options="$options" || return $?
    cp "$output_dir/installed/$executable" "$output_dir/curry-frontend" || return $?
  else
    # Start at GHC 9.6; retain solver/compile errors for named source fixes.
    if [ "$linkage" = static ]; then
      static_args=(--disable-shared --enable-executable-static)
    fi
    cabal build "exe:$executable" --verbose=3 --allow-newer \
      "${static_args[@]}" --ghc-options="$options" || return $?
    local built_binary
    built_binary=$(cabal list-bin "exe:$executable") || return $?
    cp "$built_binary" "$output_dir/curry-frontend" || return $?
  fi
  readelf -l -d "$output_dir/curry-frontend" > "$output_dir/$linkage-elf.txt" || return $?
  cat "$output_dir/$linkage-elf.txt"
  if [ "$linkage" = static ] && grep -qE 'INTERP|\(NEEDED\)' "$output_dir/$linkage-elf.txt"; then
    echo 'Static flags produced a dynamic executable; rejecting the static attempt.'
    return 1
  fi
}
if [ "$(uname -m)" != x86_64 ]; then
  cabal update --verbose=3
fi
if build_frontend static 2>&1 | tee "$output_dir/static.log"; then
  echo static > "$output_dir/linkage-requested.txt"
else
  echo 'Static attempt failed; retrying dynamic link with the same source.'
  build_frontend dynamic 2>&1 | tee "$output_dir/dynamic.log" || exit 1
  echo dynamic > "$output_dir/linkage-requested.txt"
fi
test "$("$output_dir/curry-frontend" --numeric-version)" = 2.0.0
"$output_dir/curry-frontend" --version
file "$output_dir/curry-frontend"
readelf -d -V "$output_dir/curry-frontend" > "$output_dir/elf.txt"
cat "$output_dir/elf.txt"
ghc-pkg list > "$output_dir/ghc-packages.txt"
find . -name plan.json -exec cp '{}' "$output_dir/plan.json" \;
