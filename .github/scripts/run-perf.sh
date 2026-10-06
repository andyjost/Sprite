#!/bin/bash
# Runs the suites of the nightly performance job on the C++ backend and
# writes one record file per suite under OUTDIR: throughput.jsonl (the
# fixed set of programs of run_benchmarks --nightly, REPEAT repetitions),
# compile.jsonl (the same programs and the expression item, three
# repetitions), import.jsonl (the four items, five repetitions), and
# applications.jsonl (the two applications at the sizes of the nightly job
# on the C++ backend against resolvelib and the plain-Python ranking, three
# repetitions; the clang opponent runs on request only).  The harness caps
# and times every run.  The status is 1 when a run failed or timed out; a
# slow run is not a failure.  See tests/README, section 9.
# Usage: run-perf.sh OUTDIR [LABEL]
# Environment: REPEAT (repetitions of the throughput suite, default 3),
# TIMEOUT (seconds per run, default 300), SUITES (the suites to run, default
# "throughput compile import applications").
set -uo pipefail
if [ $# -lt 1 ]; then
  echo "usage: $0 OUTDIR [LABEL]" >&2
  exit 2
fi
out=$(mkdir -p "$1" && cd "$1" && pwd)
label=${2:-nightly}
: "${REPEAT:=3}"
: "${TIMEOUT:=300}"
: "${SUITES:=throughput compile import applications}"
cd "$(dirname "$0")/../../tests"
status=0
suite() {
  local name=$1
  shift
  echo "::group::$name suite"
  if ./run_benchmarks -s "$name" --nightly --timeout "$TIMEOUT" \
      --label "$label" -o "$out/$name.jsonl" "$@"; then
    echo "$name suite: every run ok"
  else
    status=1
    echo "::error::a run of the $name suite failed"
  fi
  echo "::endgroup::"
}
for name in $SUITES; do
  case $name in
    throughput) suite throughput -b cxx -r "$REPEAT" ;;
    compile) suite compile -b cxx -r 3 ;;
    import) suite import -b cxx -r 5 ;;
    applications) suite applications -b cxx -b resolvelib -b python -r 3 ;;
    *) echo "::error::no suite $name in the nightly job"; status=1 ;;
  esac
done
exit $status
