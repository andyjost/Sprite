#!/bin/bash
# Builds the two conda packages of Sprite into a local channel.
#
# The source of the package sprite is an export of a commit (git archive of
# HEAD by default), with the pybind11 submodule exported the same way.  So an
# untracked or a modified file of the working tree never ships, and the
# links install and object-root of a developer tree stay out.  The recipe
# itself keeps `path: ../..`: inside the export that is the exported tree.
#
# Usage: conda/build-packages.sh --build-root DIR [options]
# Say --help for the options.
#
# The steps run in this order: export, curry-frontend, sprite.  conda-build
# runs in a scrubbed environment (env -i with PATH, HOME, the locale, TMPDIR,
# the proxy variables, CONDA_PKGS_DIRS, CPU_COUNT and XDG_CACHE_HOME): a
# conda environment that is active in the shell, or the variables of a conda
# compiler (CC, CXX, CFLAGS, ...), would otherwise reach the build.
# XDG_CACHE_HOME points under the build root: the test step of conda-build
# compiles a program, and the C++ backend writes the precompiled header of
# the runtime (about 70 MB, one directory per test prefix) under the cache
# directory of the user, which would otherwise be the home directory of the
# builder.  conda-build itself writes under /tmp: the activation scripts of
# the conda-forge compilers write /tmp/old-env-<pid>.txt.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$script_dir/.." && pwd)
CLEAN_PATH=${SPRITE_BUILD_CLEAN_PATH:-/usr/local/bin:/usr/bin:/bin}
# The variables of the shell that reach conda-build, when they are set.
PASS_VARIABLES=(
  HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
  NO_PROXY no_proxy CONDA_PKGS_DIRS USER LOGNAME
)

usage() {
  cat <<USAGE
usage: build-packages.sh --build-root DIR [options]

Builds the conda packages curry-frontend and sprite into a local channel
from an export of a commit of this repository.

options:
  --build-root DIR     the build root: DIR/src holds the export, DIR/bld the
                       build environments (--croot of conda-build), and
                       DIR/src_cache the source cache (required)
  --channel DIR        the output folder, which becomes the local channel
                       (default: DIR/channel under the build root)
  --conda PATH         the conda program with conda-build (default: conda)
  --rev REV            the commit to export (default: HEAD)
  --overlay PATH       take PATH (a file or a directory, relative to the
                       repository) from the working tree instead of the
                       commit; repeatable.  For a build of uncommitted work.
  --jobs N             the job count of make in the build (CPU_COUNT;
                       default: 4)
  --pakcs-archive FILE the PAKCS binary archive, copied into the source
                       cache under the name conda-build uses, so that the
                       build of curry-frontend downloads nothing
  --memory-limit GB    run each conda build under prlimit --as of this size
  --timeout SEC        the time limit of each conda build (default: 3600)
  --skip-frontend      do not build curry-frontend (the channel holds it)
  --export-only        export the commit and stop
  --dry-run            print every command, run none
  -h, --help           this text
USAGE
}

die() {
  echo "build-packages.sh: $*" >&2
  exit 1
}

build_root=
channel=
conda_exe=conda
rev=HEAD
overlays=()
jobs=4
pakcs_archive=
memory_limit=
time_limit=3600
skip_frontend=0
export_only=0
dry_run=0

while [ $# -gt 0 ]; do
  case $1 in
    --build-root) build_root=$2; shift 2 ;;
    --channel) channel=$2; shift 2 ;;
    --conda) conda_exe=$2; shift 2 ;;
    --rev) rev=$2; shift 2 ;;
    --overlay) overlays+=("$2"); shift 2 ;;
    --jobs) jobs=$2; shift 2 ;;
    --pakcs-archive) pakcs_archive=$2; shift 2 ;;
    --memory-limit) memory_limit=$2; shift 2 ;;
    --timeout) time_limit=$2; shift 2 ;;
    --skip-frontend) skip_frontend=1; shift ;;
    --export-only) export_only=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option $1 (say --help)" ;;
  esac
done
[ -n "$build_root" ] || die "--build-root is required"
build_root=$(mkdir -p "$build_root" && cd "$build_root" && pwd)
: "${channel:=$build_root/channel}"

# Prints a command, and runs it unless --dry-run.
run() {
  printf '%% %s\n' "$*"
  if [ "$dry_run" = 0 ]; then
    "$@"
  fi
}

# 1. The export.
commit=$(git -C "$repo" rev-parse --short "$rev")
submodule_rev=$(git -C "$repo" rev-parse "$rev:extern/pybind11")
src="$build_root/src/sprite-$commit"
echo "1. export of $rev ($commit) to $src"
run rm -rf "$src"
run mkdir -p "$src/extern/pybind11"
echo "% git -C $repo archive --format=tar $rev | tar -x -C $src"
if [ "$dry_run" = 0 ]; then
  git -C "$repo" archive --format=tar "$rev" | tar -x -C "$src"
fi
# A git archive of the superproject holds no file of a submodule.  The
# submodule is exported at the commit the superproject records.  Its
# checkout must hold that commit.
echo "% git -C $repo/extern/pybind11 archive --format=tar $submodule_rev | tar -x -C $src/extern/pybind11"
if [ "$dry_run" = 0 ]; then
  git -C "$repo/extern/pybind11" archive --format=tar "$submodule_rev" \
    | tar -x -C "$src/extern/pybind11"
  test -f "$src/extern/pybind11/include/pybind11/pybind11.h" \
    || die "the export of the pybind11 submodule is incomplete"
  test -f "$src/VERSION" || die "the export holds no VERSION file"
fi
# The overlays: a path of the working tree replaces the exported one.  The
# path is normalized first (realpath -m), so that . and .. components name
# the file they resolve to, and a path that leaves the repository or names
# the repository itself is refused: "conda/.." would otherwise replace the
# whole export with the working tree, and ".." the whole src directory.
for given in "${overlays[@]}"; do
  case $given in
    /*) die "--overlay $given: a path relative to the repository is needed" ;;
  esac
  path=$(realpath -m --relative-to="$repo" "$repo/$given")
  case $path in
    .|..|../*) die "--overlay $given: the path leaves the repository or names it" ;;
  esac
  test -e "$repo/$path" || die "--overlay $given: no such file in the working tree"
  run rm -rf "$src/$path"
  run mkdir -p "$(dirname "$src/$path")"
  run cp -a "$repo/$path" "$src/$path"
done
if [ "$export_only" = 1 ]; then
  exit 0
fi

# 2. The source cache: the PAKCS archive under the name conda-build uses, the
# file name with the first ten characters of its SHA-256.
if [ -n "$pakcs_archive" ]; then
  meta="$repo/conda/curry-frontend/meta.yaml"
  sha256=$(sed -n 's/^ *sha256: *\([0-9a-f]*\).*/\1/p' "$meta" | head -1)
  [ -n "$sha256" ] || die "no sha256 in $meta"
  if [ "$dry_run" = 0 ]; then
    actual=$(sha256sum "$pakcs_archive" | cut -d' ' -f1)
    [ "$actual" = "$sha256" ] \
      || die "the SHA-256 of $pakcs_archive is $actual, not $sha256"
  fi
  name=$(basename "$pakcs_archive" .tar.gz)
  run mkdir -p "$build_root/src_cache"
  run cp -p "$pakcs_archive" "$build_root/src_cache/${name}_${sha256:0:10}.tar.gz"
fi

# 3. The builds.  The scrubbed environment; the local channel first, so
# that the build of sprite takes curry-frontend from it.  The cache
# directory of the user, where the test step writes the precompiled header,
# is under the build root (see the head of this file).
cache="$build_root/cache"
scrubbed=(env -i "PATH=$CLEAN_PATH" "HOME=$HOME" LC_ALL=C.UTF-8 LANG=C.UTF-8
          "TMPDIR=${TMPDIR:-/tmp}" "CPU_COUNT=$jobs" "XDG_CACHE_HOME=$cache")
passed=()
for name in "${PASS_VARIABLES[@]}"; do
  if [ -n "${!name:-}" ]; then
    scrubbed+=("$name=${!name}")
    passed+=("$name")
  fi
done
limits=(timeout "$time_limit")
if [ -n "$memory_limit" ]; then
  limits=(prlimit "--as=$((memory_limit * 1024 * 1024 * 1024))" "${limits[@]}")
fi
conda_build() {
  local cmd=("$conda_exe" build "$1"
             --croot "$build_root/bld" --output-folder "$channel"
             --override-channels -c "file://$channel" -c conda-forge
             --no-anaconda-upload)
  # The plan names the passed variables, not their values: a proxy
  # variable can hold a credential.
  printf '%% env -i PATH=%s HOME=%s LC_ALL=C.UTF-8 LANG=C.UTF-8 TMPDIR=%s CPU_COUNT=%s XDG_CACHE_HOME=%s [%s] %s\n' \
    "$CLEAN_PATH" "$HOME" "${TMPDIR:-/tmp}" "$jobs" "$cache" "${passed[*]}" \
    "${limits[*]} ${cmd[*]}"
  if [ "$dry_run" = 0 ]; then
    "${scrubbed[@]}" "${limits[@]}" "${cmd[@]}"
  fi
}
run mkdir -p "$channel/noarch" "$channel/linux-64"
if [ "$skip_frontend" = 0 ]; then
  echo "2. curry-frontend"
  conda_build "$src/conda/curry-frontend"
fi
echo "3. sprite"
conda_build "$src/conda/recipe"
echo "done: the packages are under $channel/linux-64"
