#!/bin/bash
# Sets up a development machine for Sprite.
#
# One scratch prefix holds every bulky product: the pinned PAKCS, the conda
# environment and its package cache, the staged install, and the object
# tree.  The checkout reaches the last two through the links install and
# object-root, so a small home disk does not fill up.
#
# Usage: scripts/setup-dev-machine.sh --prefix DIR [--repo DIR] [options]
# Say --help for the options.
#
# The steps run in this order: machine, apt, pakcs, checkout, conda,
# configure, stage, smoke, next.  Each step is idempotent: a finished step
# is skipped on the next run, so the script can run again after a stop.
# configure empties install and object-root, so it is skipped while
# Make.config exists and the flags of the last run are the same
# (PREFIX/configure-args); --reconfigure forces it.  The script never runs
# sudo.  When an apt package is missing it prints the apt command for the
# user and stops.
#
# --dry-run prints every command and runs none.  The read-only probes that
# decide the plan still run: command -v, dpkg-query, and configure --help.
#
# Sources: .github/scripts/install-curry-toolchain.sh (the PAKCS and icurry
# steps), conda/dev-environment.yml (the Python packages), and the rule that
# configure and make run in a clean environment: a conda toolchain in the
# login shell exports CC, CXX, and their flags, and the Makefiles of Sprite
# append them.
set -euo pipefail

PAKCS_VERSION=${PAKCS_VERSION:-3.4.1}
ICURRY_VERSION=${ICURRY_VERSION:-3.1.0}
PAKCS_URL_BASE=https://www.curry-lang.org/pakcs/download
# SHA-256 of the PAKCS binary archive of each pinned version: the hash of
# conda/curry-frontend/meta.yaml, the archive dated 2021-10-26.  A version
# without a hash here gets its size recorded instead.
declare -A PAKCS_SHA256=(
  [3.4.1]=d17d8b3c30564200d5f4ee3a4ee9882fbca5ed66b77b9317050e1f71ba955db2
)
# The Kiel mirrors of CPM do not answer; curry-lang.org does.
CPM_INDEX_URL=https://cpm.curry-lang.org/PACKAGES/INDEX.tar.gz
CPM_TAR_URL=https://cpm.curry-lang.org/PACKAGES
REPO_URL_DEFAULT=https://github.com/andyjost/Sprite.git
# The PATH of the clean environment for configure, make, and the tests.
CLEAN_PATH=${SPRITE_SETUP_CLEAN_PATH:-/usr/local/bin:/usr/bin:/bin}
# The apt packages.  swi-prolog-nox serves PAKCS alone: the build of its
# saved states and the test oracle pakcs; Sprite itself runs no Prolog.
# time is GNU time, which the benchmark harness uses for the peak memory
# of a run.  perf comes from the linux-tools packages, which depend on the
# kernel; see perf_packages.
APT_PACKAGES=(git swi-prolog-nox g++ make curl ccache time)
NSTEPS=9

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

usage() {
  cat <<USAGE
usage: setup-dev-machine.sh --prefix DIR [--repo DIR] [options]

Sets up a development machine for Sprite: the apt packages (printed, never
installed by the script), PAKCS $PAKCS_VERSION, a conda environment, the
checkout, configure, make stage, and a smoke test.  Idempotent: run it again
after a stop.

options:
  --prefix DIR       the scratch root: DIR/pakcs-$PAKCS_VERSION, DIR/conda/env,
                     DIR/conda/pkgs, DIR/downloads, DIR/install, DIR/object-root,
                     and DIR/cpm with --icurry (required)
  --repo DIR         the Sprite checkout; cloned when missing (default: the
                     checkout that holds this script)
  --repo-url URL     the clone URL (default: $REPO_URL_DEFAULT)
  --branch NAME      the branch to clone (default: the default branch)
  --jobs N|auto      the job count given to configure when it supports --jobs
                     (default: auto: make counts the processors when it starts)
  --reconfigure      run configure although Make.config exists and the flags
                     are the ones of the last run (empties install and
                     object-root, so make stage rebuilds everything)
  --dry-run          print every command, run none
  --skip-apt         do not check the apt packages
  --icurry           also install icurry $ICURRY_VERSION through cypm, the
                     optional second route from Curry to ICurry
  --smoke-file FILE  the unit test file of the smoke test (default: unit_expr.py)
  --cap-kb N         address-space cap of each smoke run in KiB, or unlimited
                     (default: 6291456, the cap of tests/run_tests)
  --timeout SEC      time limit of each smoke run (default: 600)
  --cc PATH          the system C compiler (default: /usr/bin/gcc)
  --cxx PATH         the system C++ compiler (default: /usr/bin/g++)
  -h, --help         show this text

environment:
  PAKCS_VERSION, ICURRY_VERSION   the pinned versions (default: $PAKCS_VERSION, $ICURRY_VERSION)
  SPRITE_SETUP_CLEAN_PATH         the PATH of the clean environment
                                  (default: /usr/local/bin:/usr/bin:/bin)
USAGE
}

die() {
  echo "setup-dev-machine.sh: $*" >&2
  exit 1
}

# ----------------------------------------------------------------------------
# Options.

prefix=
repo=
repo_url=$REPO_URL_DEFAULT
branch=
jobs=auto
reconfigure=0
dry_run=0
skip_apt=0
with_icurry=0
smoke_file=unit_expr.py
cap_kb=6291456
timeout_sec=600
cc=/usr/bin/gcc
cxx=/usr/bin/g++

need_value() {
  if [ $# -lt 2 ]; then
    usage >&2
    die "option $1 needs a value"
  fi
}

while [ $# -gt 0 ]; do
  case $1 in
    --*=*)
      opt=${1%%=*}
      val=${1#*=}
      shift
      set -- "$opt" "$val" "$@"
      continue
      ;;
    --prefix) need_value "$@"; prefix=$2; shift 2 ;;
    --repo) need_value "$@"; repo=$2; shift 2 ;;
    --repo-url) need_value "$@"; repo_url=$2; shift 2 ;;
    --branch) need_value "$@"; branch=$2; shift 2 ;;
    --jobs) need_value "$@"; jobs=$2; shift 2 ;;
    --reconfigure) reconfigure=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    --skip-apt) skip_apt=1; shift ;;
    --icurry) with_icurry=1; shift ;;
    --smoke-file) need_value "$@"; smoke_file=$2; shift 2 ;;
    --cap-kb) need_value "$@"; cap_kb=$2; shift 2 ;;
    --timeout) need_value "$@"; timeout_sec=$2; shift 2 ;;
    --cc) need_value "$@"; cc=$2; shift 2 ;;
    --cxx) need_value "$@"; cxx=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      usage >&2
      die "unknown option: $1"
      ;;
  esac
done

if [ -z "$prefix" ]; then
  usage >&2
  die "--prefix is required"
fi
if [ -z "$repo" ]; then
  if [ -f "$script_dir/../configure" ]; then
    repo=$(cd "$script_dir/.." && pwd)
  else
    usage >&2
    die "--repo is required when the script does not sit in a checkout"
  fi
fi
prefix=$(realpath -m "$prefix")
repo=$(realpath -m "$repo")
case $jobs in
  auto) ;;
  ''|*[!0-9]*|0) die "--jobs needs a positive integer or auto" ;;
esac
case $cap_kb in
  unlimited) ;;
  ''|*[!0-9]*|0) die "--cap-kb needs a positive integer or unlimited" ;;
esac
case $timeout_sec in
  ''|*[!0-9]*|0) die "--timeout needs a positive integer" ;;
esac

# ----------------------------------------------------------------------------
# Derived names.

pakcs_home=$prefix/pakcs-$PAKCS_VERSION
pakcs_tarball=pakcs-$PAKCS_VERSION-amd64-Linux.tar.gz
pakcs_url=$PAKCS_URL_BASE/$pakcs_tarball
downloads=$prefix/downloads
conda_env=$prefix/conda/env
conda_pkgs=$prefix/conda/pkgs
cpm_home=$prefix/cpm
python=$conda_env/bin/python
env_file=$repo/conda/dev-environment.yml
# The flags of the last configure run; see step_configure.
configure_args_file=$prefix/configure-args
icurry_path=
# The cores of this machine, from step_machine.
cores=

# The clean environment.  A conda toolchain in the login shell exports CC,
# CXX, CFLAGS, CXXFLAGS, CPPFLAGS, and LDFLAGS, and the Makefiles append them.
# CCACHE_DIR keeps the compiler cache under the prefix in every build and
# test run, not under HOME: with configure --with-ccache the compiler of the
# installation runs ccache too, so every process that compiles a Curry
# module for the C++ backend reads the variable.
clean_env=(env -i "PATH=$CLEAN_PATH" "HOME=$HOME" LC_ALL=C.UTF-8)
if [ -n "${TMPDIR:-}" ]; then
  clean_env+=("TMPDIR=$TMPDIR")
fi
clean_env+=("CCACHE_DIR=$prefix/ccache")

# ----------------------------------------------------------------------------
# Output and execution.

stops=()

step() {
  printf '\n==> %s\n' "$*"
}

note() {
  printf '    %s\n' "$*"
}

quoted() {
  local out="" arg
  for arg in "$@"; do
    out+=" $(printf '%q' "$arg")"
  done
  printf '%s' "${out# }"
}

# Prints a command and runs it, unless this is a dry run.
run() {
  printf '    + %s\n' "$(quoted "$@")"
  if [ "$dry_run" = 0 ]; then
    "$@"
  fi
}

# Prints a shell snippet and runs it, unless this is a dry run.
run_shell() {
  printf '    + %s\n' "$1"
  if [ "$dry_run" = 0 ]; then
    bash -c "$1"
  fi
}

# The same, in a directory.
run_in() {
  local dir=$1
  shift
  printf '    + (cd %s && %s)\n' "$(quoted "$dir")" "$(quoted "$@")"
  if [ "$dry_run" = 0 ]; then
    (cd "$dir" && "$@")
  fi
}

# The same, in a directory, and a failure does not stop the script.
run_in_ok() {
  local dir=$1
  shift
  printf '    + (cd %s && %s) || true\n' "$(quoted "$dir")" "$(quoted "$@")"
  if [ "$dry_run" = 0 ]; then
    (cd "$dir" && "$@") || note "exit status $?; continuing"
  fi
}

# The same, in a directory, under an address-space cap in KiB.
run_in_capped() {
  local dir=$1 kb=$2
  shift 2
  printf '    + (cd %s && ulimit -v %s && %s)\n' \
      "$(quoted "$dir")" "$kb" "$(quoted "$@")"
  if [ "$dry_run" = 0 ]; then
    (cd "$dir" && ulimit -v "$kb" && "$@")
  fi
}

# A real run stops here; a dry run records the stop and goes on, so that the
# plan is complete.
stop_here() {
  if [ "$dry_run" = 1 ]; then
    note "(dry run: a real run stops here: $*)"
    stops+=("$*")
  else
    die "$*"
  fi
}

# ----------------------------------------------------------------------------
# Step 1: the machine.

gib() {
  # kB of /proc/meminfo to GiB with one decimal.
  awk -v kb="$1" 'BEGIN { printf "%.1f", kb / 1048576 }'
}

step_machine() {
  step "Step 1/$NSTEPS: machine"
  local os mem swap found=() missing=() tool
  os=$(sed -n 's/^PRETTY_NAME="\(.*\)"/\1/p' /etc/os-release 2>/dev/null || true)
  cores=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN)
  mem=$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo 2>/dev/null || echo 0)
  swap=$(awk '/^SwapTotal:/ { print $2 }' /proc/meminfo 2>/dev/null || echo 0)
  note "os: ${os:-unknown}"
  note "cores: $cores  memory: $(gib "$mem") GiB  swap: $(gib "$swap") GiB"
  # auto goes to configure as it is: make counts the processors when it
  # starts, so Make.config carries no count of this machine.
  if [ "$jobs" = auto ]; then
    note "jobs: auto (one per processor, counted by make; $cores now)"
  else
    note "jobs: $jobs"
  fi
  note "prefix: $prefix"
  note "repo: $repo"
  for tool in bash git curl tar make "$cc" "$cxx" swipl sha256sum \
      micromamba mamba conda ccache perf /usr/bin/time; do
    if command -v "$tool" >/dev/null 2>&1; then
      found+=("$tool")
    else
      missing+=("$tool")
    fi
  done
  note "found: ${found[*]}"
  if [ ${#missing[@]} -gt 0 ]; then
    note "missing: ${missing[*]}"
  fi
  case $os in
    Ubuntu*|Debian*) ;;
    *) note "not Ubuntu or Debian: the apt step needs --skip-apt and the equivalents of the packages" ;;
  esac
}

# ----------------------------------------------------------------------------
# Step 2: the apt packages.

perf_packages() {
  # perf lives in the linux-tools package of the running kernel.  Without
  # one, the generic package follows the generic kernel.
  local kernel
  kernel=$(uname -r)
  if command -v apt-cache >/dev/null 2>&1 \
      && apt-cache show "linux-tools-$kernel" >/dev/null 2>&1; then
    echo "linux-tools-common linux-tools-$kernel"
  else
    echo "linux-tools-common linux-tools-generic"
  fi
}

step_apt() {
  step "Step 2/$NSTEPS: apt packages"
  if [ "$skip_apt" = 1 ]; then
    note "skipped (--skip-apt)"
    return
  fi
  if ! command -v dpkg-query >/dev/null 2>&1; then
    note "dpkg-query not found, so this is not a Debian or Ubuntu system."
    note "Install the equivalents of ${APT_PACKAGES[*]} and perf, then run again with --skip-apt."
    stop_here "apt: no dpkg"
    return
  fi
  local pkgs missing=() pkg status
  read -r -a pkgs <<<"${APT_PACKAGES[*]} $(perf_packages)"
  for pkg in "${pkgs[@]}"; do
    status=$(dpkg-query -W -f='${db:Status-Status}' "$pkg" 2>/dev/null || true)
    if [ "$status" != installed ]; then
      missing+=("$pkg")
    fi
  done
  if [ ${#missing[@]} -eq 0 ]; then
    note "installed: ${pkgs[*]}"
    return
  fi
  note "missing: ${missing[*]}"
  note "The script does not run sudo.  Run this command, then run the script again:"
  printf '\n        sudo apt-get update && sudo apt-get install -y --no-install-recommends %s\n\n' \
      "${missing[*]}"
  stop_here "apt: ${#missing[@]} package(s) missing"
}

# ----------------------------------------------------------------------------
# Step 3: PAKCS.

pakcs_built() {
  # make writes the REPL state src/pakcs; bin/pakcs runs it.
  [ -x "$pakcs_home/src/pakcs" ] && [ -x "$pakcs_home/bin/pakcs-frontend" ]
}

step_pakcs() {
  step "Step 3/$NSTEPS: PAKCS $PAKCS_VERSION under $pakcs_home"
  if pakcs_built; then
    note "built: $pakcs_home (bin/pakcs, bin/pakcs-frontend)"
    return
  fi
  local swipl expected tarball=$downloads/$pakcs_tarball
  swipl=$(PATH=$CLEAN_PATH command -v swipl || true)
  if [ -z "$swipl" ]; then
    swipl=$(command -v swipl || true)
  fi
  if [ -z "$swipl" ]; then
    stop_here "pakcs: swipl not found (package swi-prolog-nox)"
    swipl=swipl
  fi
  if [ -f "$tarball" ]; then
    note "archive present: $tarball"
  else
    run mkdir -p "$downloads"
    run curl -fsSL -o "$tarball" "$pakcs_url"
  fi
  expected=${PAKCS_SHA256[$PAKCS_VERSION]:-}
  if [ -n "$expected" ]; then
    note "checksum (SHA-256 of conda/curry-frontend/meta.yaml): $expected"
    run_shell "echo $(quoted "$expected  $tarball") | sha256sum -c -"
  else
    note "no pinned checksum for PAKCS $PAKCS_VERSION; the size is recorded instead:"
    run_shell "stat -c '%s bytes  %n' $(quoted "$tarball") && sha256sum $(quoted "$tarball")"
  fi
  if [ -d "$pakcs_home" ]; then
    note "unpacked: $pakcs_home"
  else
    run tar xzf "$tarball" -C "$prefix"
    if [ "$dry_run" = 0 ] && [ ! -d "$pakcs_home" ]; then
      die "the archive did not unpack to $pakcs_home"
    fi
  fi
  # The distribution sets a stack limit for SWI-Prolog 8 only.  Give 9 the
  # same (the CI script does too).  The pattern matches only before the
  # change, so the edit is idempotent.
  if [ "$dry_run" = 1 ] || grep -q '^[[:space:]]*8 )' "$pakcs_home/scripts/pakcs-makesavedstate.sh"; then
    run sed -i 's/^\([[:space:]]*\)8 )/\18 | 9 )/' "$pakcs_home/scripts/pakcs-makesavedstate.sh"
  fi
  note "make builds the saved states (several minutes)"
  run_in "$pakcs_home" "${clean_env[@]}" make "SWIPROLOG=$swipl"
  if [ "$dry_run" = 0 ]; then
    pakcs_built || die "PAKCS did not build: $pakcs_home/src/pakcs is missing"
    note "pakcs --numeric-version: $(LC_ALL=C.UTF-8 "$pakcs_home/bin/pakcs" --numeric-version)"
    note "pakcs-frontend --numeric-version: $("$pakcs_home/bin/pakcs-frontend" --numeric-version)"
  fi
}

# ----------------------------------------------------------------------------
# Step 5: the conda environment.

conda_tool() {
  local tool
  for tool in micromamba mamba conda; do
    if command -v "$tool" >/dev/null 2>&1; then
      echo "$tool"
      return
    fi
  done
}

conda_env_satisfied() {
  [ -x "$python" ] \
    && "$python" -c 'import sys; assert sys.version_info[:2] == (3, 14)' 2>/dev/null \
    && "$python" -c 'import numpy, sphinx, sphinx_rtd_theme' 2>/dev/null
}

step_conda() {
  step "Step 5/$NSTEPS: conda environment $conda_env"
  note "environment file: $env_file"
  note "package cache: $conda_pkgs (CONDA_PKGS_DIRS)"
  if conda_env_satisfied; then
    note "satisfied: $("$python" --version) with numpy, sphinx, sphinx_rtd_theme"
    return
  fi
  local tool
  tool=$(conda_tool)
  if [ -z "$tool" ]; then
    note "none of micromamba, mamba, conda is on PATH.  Install one (micromamba"
    note "is a single binary; see mamba.readthedocs.io), then run again, or run:"
    printf '\n        CONDA_PKGS_DIRS=%s conda env create -y -p %s -f %s\n\n' \
        "$(quoted "$conda_pkgs")" "$(quoted "$conda_env")" "$(quoted "$env_file")"
    stop_here "conda: no conda tool"
    return
  fi
  if [ "$dry_run" = 0 ] && [ ! -f "$env_file" ]; then
    die "environment file not found: $env_file (clone first?)"
  fi
  run mkdir -p "$conda_pkgs"
  if [ -x "$python" ]; then
    note "the environment exists but lacks a package: updating it"
    case $tool in
      micromamba) run env "CONDA_PKGS_DIRS=$conda_pkgs" micromamba install -y -p "$conda_env" -f "$env_file" ;;
      *) run env "CONDA_PKGS_DIRS=$conda_pkgs" "$tool" env update -p "$conda_env" -f "$env_file" --prune ;;
    esac
  else
    case $tool in
      micromamba) run env "CONDA_PKGS_DIRS=$conda_pkgs" micromamba create -y -p "$conda_env" -f "$env_file" ;;
      *) run env "CONDA_PKGS_DIRS=$conda_pkgs" "$tool" env create -y -p "$conda_env" -f "$env_file" ;;
    esac
  fi
  if [ "$dry_run" = 0 ]; then
    conda_env_satisfied || die "the conda environment is not complete: $python lacks Python 3.14, numpy, sphinx, or sphinx_rtd_theme"
    note "ready: $("$python" --version)"
  fi
}

# ----------------------------------------------------------------------------
# Step 4: the checkout and its links.

link_tree() {
  # Links $repo/$name to $prefix/$name.  An existing link to the same place
  # is fine.  Anything else is left alone, and the script stops.
  local name=$1 target=$prefix/$1 link=$repo/$1
  run mkdir -p "$target"
  if [ -L "$link" ]; then
    if [ "$(readlink -f "$link")" = "$(readlink -f "$target")" ]; then
      note "$name -> $target (present)"
    else
      note "$link points to $(readlink "$link"), not to $target."
      note "Move it away (the script deletes nothing), then run again."
      stop_here "clone: $name points elsewhere"
    fi
  elif [ -e "$link" ]; then
    note "$link exists and is not a link.  Move it away, then run again."
    stop_here "clone: $name is not a link"
  else
    run ln -s "$target" "$link"
  fi
}

step_clone() {
  step "Step 4/$NSTEPS: checkout $repo"
  if [ -f "$repo/configure" ]; then
    note "present: $repo"
  else
    if [ -e "$repo" ]; then
      note "$repo exists but holds no configure script"
      stop_here "clone: $repo is not a Sprite checkout"
      return
    fi
    if [ -n "$branch" ]; then
      run git clone --branch "$branch" "$repo_url" "$repo"
    else
      run git clone "$repo_url" "$repo"
    fi
  fi
  # Only pybind11 is needed for the build.
  run git -C "$repo" submodule update --init extern/pybind11
  link_tree install
  link_tree object-root
}

# ----------------------------------------------------------------------------
# Step 6: configure.

configure_help() {
  # The usage text of configure, to probe for options it may gain later.
  # Read-only; empty when the checkout or a Python is missing.
  local py
  for py in "$python" python3; do
    if command -v "$py" >/dev/null 2>&1 && [ -f "$repo/configure" ]; then
      (cd "$repo" && "$py" ./configure --help 2>/dev/null) && return
    fi
  done
  return 0
}

step_configure() {
  step "Step 6/$NSTEPS: configure"
  local help flags ccache_bin wanted recorded=
  flags=(
      "--with-python=$python"
      "--with-cc=$cc"
      "--with-cxx=$cxx"
      "--with-cxx-postinstall=$cxx"
      "--with-pakcs=$pakcs_home/bin/pakcs"
      "--with-icurry=$icurry_path"
    )
  help=$(configure_help || true)
  if [ -z "$help" ]; then
    note "configure --help could not be probed (no checkout yet); --jobs and --with-ccache are left out"
  fi
  if grep -q -- '--jobs' <<<"$help"; then
    flags+=("--jobs=$jobs")
  else
    note "configure has no --jobs option yet: the build runs as configure decides"
  fi
  ccache_bin=$(PATH=$CLEAN_PATH command -v ccache || true)
  if grep -q -- '--with-ccache' <<<"$help" && [ -n "$ccache_bin" ]; then
    flags+=("--with-ccache=$ccache_bin")
    note "compiler cache: $prefix/ccache (CCACHE_DIR of the clean environment)"
  else
    note "configure has no --with-ccache option yet, or ccache is missing: no compiler cache"
  fi
  note "clean environment: ${clean_env[*]}"
  # configure empties install and object-root when it writes Make.config.
  # So a run with the flags of the last run skips it, and a stop after this
  # step (a failed smoke test, say) does not cost a rebuild.
  wanted=$(printf '%s\n' "${flags[@]}")
  if [ -f "$configure_args_file" ]; then
    recorded=$(cat "$configure_args_file")
  fi
  if [ "$reconfigure" = 0 ] && [ -f "$repo/Make.config" ] \
      && [ -n "$recorded" ] && [ "$recorded" = "$wanted" ]; then
    note "skipped: Make.config exists and $configure_args_file holds the same flags"
    note "(configure empties install and object-root; --reconfigure forces it)"
    return
  fi
  if [ "$dry_run" = 0 ] && [ -f "$repo/Make.config" ]; then
    # Every object depends on Make.config.  Keep its time stamp when the
    # text does not change, so an unchanged configuration rebuilds nothing.
    cp -p "$repo/Make.config" "$repo/Make.config.setup-previous"
  fi
  run_in "$repo" "${clean_env[@]}" "$python" ./configure "${flags[@]}"
  if [ "$dry_run" = 0 ] && [ -f "$repo/Make.config.setup-previous" ]; then
    if cmp -s "$repo/Make.config" "$repo/Make.config.setup-previous"; then
      mv "$repo/Make.config.setup-previous" "$repo/Make.config"
      note "Make.config is unchanged; its time stamp is kept"
    else
      rm -f "$repo/Make.config.setup-previous"
      note "Make.config changed"
    fi
  fi
  note "the flags are recorded in $configure_args_file"
  if [ "$dry_run" = 0 ]; then
    mkdir -p "$prefix"
    printf '%s\n' "${flags[@]}" > "$configure_args_file"
  fi
}

# ----------------------------------------------------------------------------
# Step 7: make stage.

step_stage() {
  step "Step 7/$NSTEPS: make stage"
  note "builds the runtime and compiles the Curry library for both backends (minutes)"
  run_in "$repo" "${clean_env[@]}" make stage
  if [ "$dry_run" = 0 ] && [ ! -r "$prefix/install/lib/libcyrt.so" ]; then
    die "make stage did not produce $prefix/install/lib/libcyrt.so"
  fi
  # The archived products of the test programs, after the stage: they must
  # be newer than the installed library interfaces, or the front end makes
  # them again at the first test run, and one test program needs a
  # preprocessor that the PAKCS distribution lacks (tests/README, section
  # 10).
  note "extracts the archived products of the test programs (make overlay)"
  run_in "$repo" "${clean_env[@]}" make overlay
}

# ----------------------------------------------------------------------------
# Step 8: the smoke test.

step_smoke() {
  step "Step 8/$NSTEPS: smoke test ($smoke_file on each backend)"
  local backend test_env
  note "cap: $cap_kb KiB of address space; time limit: $timeout_sec s"
  run mkdir -p "$repo/tests/.cache"
  for backend in py cxx; do
    test_env=(
        "${clean_env[@]}"
        "SPRITE_HOME=$prefix/install"
        "PYTHONPATH=$repo/tests/lib"
        "CURRYPATH=$repo/tests/data/curry"
        "SPRITE_CACHE_FILE=$repo/tests/.cache/icurry.db"
        "SPRITE_INTERPRETER_FLAGS=backend:$backend"
      )
    run_in_capped "$repo/tests" "$cap_kb" "${test_env[@]}" \
        timeout "$timeout_sec" "$prefix/install/bin/python" -B -m unittest discover \
        "$repo/tests" "$smoke_file"
    if [ "$dry_run" = 0 ]; then
      note "$backend backend: ok"
    fi
  done
}

# ----------------------------------------------------------------------------
# Step 3b, optional: icurry.  Step 9: the next steps.

cpmrc_text() {
  echo "REPOSITORYPATH=$cpm_home/index"
  echo "PACKAGEINSTALLPATH=$cpm_home/packages"
  echo "BININSTALLPATH=$cpm_home/bin"
  echo "APPPACKAGEPATH=$cpm_home/app_packages"
  echo "HOMEPACKAGEPATH=$cpm_home/pakcs-$PAKCS_VERSION-homepackage"
  echo "PACKAGEINDEXURL=$CPM_INDEX_URL"
  echo "PACKAGETARFILESURL=$CPM_TAR_URL"
}

step_icurry() {
  # A port of the icurry part of .github/scripts/install-curry-toolchain.sh.
  # The CPM configuration file lives in HOME; an existing one is kept.
  local cpmrc=$HOME/.cpmrc bindir src dir cpm_env smoke
  if [ -f "$cpmrc" ]; then
    bindir=$(sed -n 's/^BININSTALLPATH=//p' "$cpmrc" | tail -n 1)
    bindir=${bindir:-$HOME/.cpm/bin}
    note "$cpmrc exists and is kept; binaries go to $bindir"
  else
    bindir=$cpm_home/bin
    note "writing $cpmrc (CPM home under $cpm_home)"
    printf '    + cat > %s <<CPMRC\n' "$(quoted "$cpmrc")"
    cpmrc_text | sed 's/^/      /'
    echo '      CPMRC'
    if [ "$dry_run" = 0 ]; then
      cpmrc_text > "$cpmrc"
    fi
  fi
  icurry_path=$bindir/icurry
  if [ -x "$icurry_path" ]; then
    note "present: $icurry_path"
    return
  fi
  cpm_env=(env -i "PATH=$pakcs_home/bin:$CLEAN_PATH" "HOME=$HOME" LC_ALL=C.UTF-8)
  src=$cpm_home/src
  run mkdir -p "$src"
  run "${cpm_env[@]}" cypm update
  # cypm names the checkout directory after the package; older versions
  # append the version.
  dir=
  for dir in "$src/icurry" "$src/icurry-$ICURRY_VERSION"; do
    if [ -d "$dir" ]; then
      break
    fi
    dir=
  done
  if [ -z "$dir" ]; then
    run_in "$src" "${cpm_env[@]}" cypm checkout icurry "$ICURRY_VERSION"
    dir=$src/icurry
    if [ "$dry_run" = 0 ] && [ ! -d "$dir" ]; then
      dir=$src/icurry-$ICURRY_VERSION
    fi
  fi
  # cypm install resolves the dependencies and builds the executable.  It
  # has been seen to exit 1 after computing the load path; build by hand
  # then.
  run_in_ok "$dir" "${cpm_env[@]}" cypm install
  if [ "$dry_run" = 1 ] || [ ! -x "$icurry_path" ]; then
    run_in "$dir" "${cpm_env[@]}" cypm exec pakcs --nocypm :set v1 :load ICurry.Main :save :quit
    run mkdir -p "$bindir"
    run mv "$dir/ICurry.Main" "$icurry_path"
  fi
  if [ "$dry_run" = 0 ]; then
    smoke=$(mktemp -d)
    printf 'main :: Int\nmain = 42\n' > "$smoke/Smoke.curry"
    run_in "$smoke" "${cpm_env[@]}" "$icurry_path" Smoke
    test -s "$smoke/.curry/pakcs-$PAKCS_VERSION/Smoke.icy" \
      || die "icurry did not write $smoke/.curry/pakcs-$PAKCS_VERSION/Smoke.icy"
    rm -rf "$smoke"
    note "ready: $icurry_path"
  fi
}

step_next() {
  step "Step 9/$NSTEPS: next steps"
  cat <<NEXT
    The machine is set up.  Paths for the personal rules file:

        python:      $python
        PAKCS:       $pakcs_home/bin (pakcs, cypm, pakcs-frontend)
        icurry:      ${icurry_path:-not installed (rerun with --icurry)}
        checkout:    $repo
        install:     $prefix/install (link: $repo/install)
        object-root: $prefix/object-root (link: $repo/object-root)
        conda cache: $conda_pkgs (CONDA_PKGS_DIRS)
        ccache:      $prefix/ccache (CCACHE_DIR)
        clean env:   ${clean_env[*]}

    1. Calibrate the test manifest on this machine: run every test file
       once per backend on a quiet machine with the manifest update of the
       test runner (see ./run_tests -h and section 10 of tests/README):

           cd $repo/tests
           ./run_tests -j 1 --backend both --update-manifest

       The durations and the peak memory of the files are then measured
       here and not copied from another machine.  Commit tests/manifest.json.
    2. Record a baseline with the benchmark harness on a quiet machine,
       with the deterministic columns (steps, forks, collections) that
       the compare command checks:

           cd $repo/tests
           ./run_benchmarks -b cxx -b py --label baseline -o $prefix/baseline.jsonl
           ./run_benchmarks counters $prefix/baseline.jsonl

    3. Update the personal rules file (CLAUDE.local.md at the checkout root)
       with the paths above, the core count ($cores) and the memory of this
       machine, and the apt packages that were installed.  Builds and tests
       outside the clean environment need CCACHE_DIR as well, or say once:
       ccache --set-config cache_dir=$prefix/ccache
    4. Optional: copy tests/.cache/icurry.db from the old machine.  It is
       keyed by the source text, so the first suite run compiles nothing.
NEXT
}

# ----------------------------------------------------------------------------

main() {
  echo "setup-dev-machine.sh: prefix=$prefix repo=$repo dry_run=$dry_run"
  step_machine
  step_apt
  step_pakcs
  if [ "$with_icurry" = 1 ]; then
    step "Step 3b: icurry $ICURRY_VERSION (optional)"
    step_icurry
  fi
  step_clone
  step_conda
  step_configure
  step_stage
  step_smoke
  step_next
  if [ "$dry_run" = 1 ]; then
    echo
    if [ ${#stops[@]} -gt 0 ]; then
      echo "dry run complete; a real run stops at: ${stops[*]}"
    else
      echo "dry run complete; no stop expected"
    fi
  else
    echo
    echo "setup complete"
  fi
}

main
