#!/bin/bash
# Appends record files of the benchmark harness to the history branch of
# the repository and pushes it.  The branch (perf-history, or
# HISTORY_BRANCH) holds the records of every run of the nightly performance
# job and the points of the chart page; the history command of the harness
# (tests/lib/benchmarks/history.py) writes both and prints each new record
# against the previous record of its item.  The script runs inside a
# checkout of the repository: it fetches the branch from the remote (origin,
# or HISTORY_REMOTE) into a worktree of its own, or starts the branch when
# the remote has none, commits, and pushes.  A push that the remote rejects
# because the branch moved is tried again from a fresh fetch, three times
# in all.  The comparison also goes to the step summary of GitHub Actions
# when GITHUB_STEP_SUMMARY is set.  Needs git 2.42 or later (the orphan
# worktree).  See tests/README, section 9.
# Usage: perf-history.sh FILE...
# Environment: HISTORY_BRANCH, HISTORY_REMOTE, PYTHON (the interpreter that
# runs the harness; python3), RUNNER_TEMP (where the worktree goes; a fresh
# temporary directory), GITHUB_SERVER_URL, GITHUB_REPOSITORY, and
# GITHUB_RUN_ID (the run named in the commit message).
set -euo pipefail
if [ $# -eq 0 ]; then
  echo "usage: $0 FILE..." >&2
  exit 2
fi
branch=${HISTORY_BRANCH:-perf-history}
remote=${HISTORY_REMOTE:-origin}
python=${PYTHON:-python3}
root=$(git rev-parse --show-toplevel)
files=()
for file in "$@"; do
  files+=("$(realpath "$file")")
done
dir=${RUNNER_TEMP:-$(mktemp -d)}/perf-history
export PYTHONPATH="$root/tests/lib${PYTHONPATH:+:$PYTHONPATH}"
name='github-actions[bot]'
email='41898282+github-actions[bot]@users.noreply.github.com'
message="Append the records of $(date -u +%Y-%m-%d)"
if [ -n "${GITHUB_RUN_ID:-}" ]; then
  server=${GITHUB_SERVER_URL:-https://github.com}
  run_url="$server/${GITHUB_REPOSITORY:-}/actions/runs/$GITHUB_RUN_ID"
  message="$message

$run_url"
fi
created=
log=$(mktemp)
cleanup() {
  git -C "$root" worktree remove --force "$dir" 2>/dev/null || true
  rm -rf "$dir"
  if [ -n "$created" ]; then
    git -C "$root" branch -D "$branch" >/dev/null 2>&1 || true
    created=
  fi
}
finish() {
  cleanup
  rm -f "$log"
}
trap finish EXIT
for attempt in 1 2 3; do
  cleanup
  if git -C "$root" fetch --quiet --depth=1 "$remote" "refs/heads/$branch" \
      2>/dev/null; then
    git -C "$root" worktree add --quiet --detach "$dir" FETCH_HEAD
  else
    echo "$remote has no branch $branch: starting it"
    git -C "$root" worktree add --quiet --orphan -b "$branch" "$dir"
    created=1
  fi
  "$python" -m benchmarks history "$dir" "${files[@]}" | tee "$log"
  git -C "$dir" add -A
  if ! git -C "$dir" -c "user.name=$name" -c "user.email=$email" \
      commit --quiet -m "$message"; then
    echo "nothing to commit"
    exit 0
  fi
  if git -C "$dir" push --quiet "$remote" "HEAD:refs/heads/$branch"; then
    echo "pushed $branch of $remote"
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
      {
        echo '## Against the previous run'
        echo
        echo '```'
        cat "$log"
        echo '```'
      } >> "$GITHUB_STEP_SUMMARY"
    fi
    exit 0
  fi
  echo "the push to $branch was rejected (attempt $attempt of 3)"
done
exit 1
