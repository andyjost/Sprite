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
# products of the front end from the product directories of the test corpus
# (the ICurry, the JSON and the interfaces), so the worktree does not run
# the front end again.  The copies get the time of the copy, not the time
# of the original (tar -m): the sources of the fresh checkout are newer
# than the originals, and a copy with the old time would count as stale
# and send every module through the front end again.  The JSON files are
# touched after the copy, so each one is newer than its ICurry file.  The
# copy follows the stage for the reason the root Makefile gives at its
# default goal: the front end compiles a module again when the interfaces
# of the installed library are newer than its products.
#
# The generated code of both backends is not copied.  The generated Python
# (and its bytecode) names the source of the tree it was made in, and the
# Python backend writes it again in a moment.  The compiled products of the
# C++ backend (the generated C++, the shared object and its ABI stamp) are
# not copied either: the stamp of a copied object names the installation it
# was compiled under, so the copy would be stale here.  The prepare pass
# of the test runner compiles them (tests/run_tests --prepare-only) and
# stores them in the product cache (SPRITE_PRODUCT_CACHE); a cache the two
# trees share serves the worktree the products of the main tree, because
# the key names no tree and an object names no path (its imports enter it
# by SONAME; the dated TODO entry of 2026-10-08 on portable objects).  With
# SPRITE_WORKTREE_PREPARE=1 the pass runs at the end of this script, on the
# C++ backend; it takes minutes on a cold tree and needs the Curry front
# end.
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
# A worktree starts with empty submodule directories.  Only pybind11 is
# needed for the build; initializing it alone writes nothing to the
# repository's config when the main tree has it registered already.
git -C "$path" submodule update --init extern/pybind11
mkdir -p "$root/install" "$root/object-root"
ln -s "$root/install" "$path/install"
ln -s "$root/object-root" "$path/object-root"
# Make.config carries the build settings of this tree, among them JOBS
# (configure --jobs) and CCACHE (configure --with-ccache), so the worktree
# builds with the same job count and the same compiler cache.  To build it
# with another count once, set MAKEFLAGS=-jN in the environment: a -j wins
# over JOBS.
cp "$here/Make.config" "$path/Make.config"
if [ -e "$here/CLAUDE.local.md" ]; then
  cp -P "$here/CLAUDE.local.md" "$path/CLAUDE.local.md"
fi
make -C "$path" stage
# The generated code of both backends stays behind (see above).
exclude=(
  --exclude='*.cpp' --exclude='*.so' --exclude='*.so.abi'
  --exclude='*.py' --exclude='*.pyc' --exclude='__pycache__'
)
(
  cd "$here"
  find curry tests/data -type d -name .curry | while read -r dir; do
    mkdir -p "$path/$dir"
    tar -C "$dir" -cf - "${exclude[@]}" . | tar -C "$path/$dir" -xmf -
    find "$path/$dir" -name '*.json.z' -exec touch {} +
  done
)
if [ "${SPRITE_WORKTREE_PREPARE:-}" = 1 ]; then
  echo "compiling the shared Curry products of the test pool (the prepare pass)"
  (cd "$path/tests" && ./run_tests --prepare-only --backend cxx)
fi
echo "worktree ready: $path (branch $branch, build under $root)"
