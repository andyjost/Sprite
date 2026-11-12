#!/bin/bash
# Updates the CPM index, or keeps the restored index during a server outage.
# The docs job caches the index and package tarballs after a fresh update.
# Output: fresh=true or fresh=false in GITHUB_OUTPUT, when set.
set -euo pipefail

if timeout 600 cypm update; then
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo 'fresh=true' >> "$GITHUB_OUTPUT"
  fi
  exit 0
fi

if [ -f "$HOME/.cpm/index/README.md" ]; then
  cached_date=$(date -u -r "$HOME/.cpm/index/README.md" '+%Y-%m-%d %H:%M:%S UTC')
  echo "::warning title=CPM server unreachable::Using the cached package index from $cached_date."
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo 'fresh=false' >> "$GITHUB_OUTPUT"
  fi
  exit 0
fi

echo '::error title=Infrastructure failure::The CPM server did not answer and no cached index exists.'
exit 1
