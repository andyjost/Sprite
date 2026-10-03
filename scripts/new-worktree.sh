#!/bin/bash
# Creates a git worktree with its own staged install, for work on several
# branches at once.
#
# Usage: scripts/new-worktree.sh <path> <branch> [<start-point>]
#
# The install and object trees of the worktree go under $SPRITE_WORKTREE_ROOT
# (default: ~/.cache/sprite/worktrees/<name>), so a small home directory does
# not fill up.  Make.config is copied from this tree, so no configure run is
# needed.  The script runs `make stage` in the worktree; run it under a clean
# environment if a conda toolchain is active.  Afterwards it copies the
# compiled caches of the Curry library and of the test corpus, so the worktree
# does not recompile them.  The copies are made after the build, so they are
# newer than the worktree's runtime library and count as up to date.
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "usage: $0 <path> <branch> [<start-point>]" >&2
  exit 2
fi
here=$(cd "$(dirname "$0")/.." && pwd)
path=$1
branch=$2
start=${3:-HEAD}
name=$(basename "$path")
root=${SPRITE_WORKTREE_ROOT:-$HOME/.cache/sprite/worktrees}/$name

git -C "$here" worktree add -b "$branch" "$path" "$start"
# A worktree starts with empty submodule directories.
git -C "$path" submodule update --init --recursive
mkdir -p "$root/install" "$root/object-root"
ln -s "$root/install" "$path/install"
ln -s "$root/object-root" "$path/object-root"
cp "$here/Make.config" "$path/Make.config"
if [ -e "$here/CLAUDE.local.md" ]; then
  cp -P "$here/CLAUDE.local.md" "$path/CLAUDE.local.md"
fi
make -C "$path" stage
(
  cd "$here"
  find curry tests/data -type d -name .curry | while read -r dir; do
    mkdir -p "$path/$(dirname "$dir")"
    cp -r "$dir" "$path/$dir"
  done
)
echo "worktree ready: $path (branch $branch, build under $root)"
