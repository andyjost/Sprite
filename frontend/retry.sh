#!/usr/bin/env bash
# Retry transient failures in network setup commands.
for attempt in 1 2 3; do
  if "$@"; then
    exit 0
  else
    status=$?
  fi
  printf 'Attempt %s/3 failed with status %s\n' "$attempt" "$status" >&2
  if [ "$attempt" -lt 3 ]; then
    sleep "${RETRY_PAUSE:-15}"
  fi
done
exit "$status"
