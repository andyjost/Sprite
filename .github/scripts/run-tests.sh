#!/bin/bash
# Runs the test files that match a pattern on one backend, one process per
# file, so that an abort in the C++ runtime fails one file and not the run.
# Usage: run-tests.sh py|cxx 'unit_*.py' [k/n]
# With k/n, only every n-th file starting at the k-th (1-based) runs, so that
# a matrix can spread the files over several runners.  SPRITE_TEST_FLAGS in
# the environment adds interpreter flags to the backend flag, in the syntax
# of SPRITE_INTERPRETER_FLAGS (for one, interpret:all).
set -uo pipefail
backend=$1
pattern=$2
shard=${3:-1/1}
k=${shard%/*}
n=${shard#*/}
cd "$(dirname "$0")/../../tests"
export SPRITE_HOME
SPRITE_HOME="$(cd ../install && pwd)"
export PYTHONPATH="$PWD/lib"
export CURRYPATH="$PWD/data/curry"
extra="${SPRITE_TEST_FLAGS:+,$SPRITE_TEST_FLAGS}"
export SPRITE_INTERPRETER_FLAGS="backend:$backend$extra"
export LC_ALL=C.UTF-8
# The ICurry cache keeps the output of the Curry front end between runs; the
# workflow restores and saves its directory.  The directory exists even when
# no test compiles Curry, so the save step has something to save.
export SPRITE_CACHE_FILE="${SPRITE_CACHE_FILE-$PWD/.cache/icurry.db}"
mkdir -p "$(dirname "$SPRITE_CACHE_FILE")"
# A diverging program fails with an allocation error instead of taking the
# machine down.
ulimit -v 6291456
failed=()
index=0
for file in $(ls $pattern | sort); do
  index=$((index + 1))
  if [ $(( (index - 1) % n + 1 )) -ne "$k" ]; then
    continue
  fi
  echo "::group::$backend $file"
  start=$(date +%s)
  if timeout 1800 "$SPRITE_HOME/bin/python" -B -m unittest discover "$PWD" "$file"; then
    status=ok
  else
    status=FAILED
    failed+=("$file")
  fi
  echo "$backend $file $status $(( $(date +%s) - start ))s"
  echo "::endgroup::"
  if [ "$status" = FAILED ]; then
    echo "::error::$backend $file failed"
  fi
done
if [ ${#failed[@]} -gt 0 ]; then
  echo "failed on the $backend backend: ${failed[*]}"
  exit 1
fi
echo "all files of shard $shard passed on the $backend backend"
