#!/bin/bash
# Builds Sprite into the conda prefix.  conda-build sets PREFIX, SRC_DIR,
# PYTHON, SP_DIR, CC, CXX, HOST, and CPU_COUNT.  See ../README.md.
set -euo pipefail

# Sprite's installation tree has its own bin/python and bin/coverage links.
# They must not replace the ones of the environment, so the tree goes under
# opt/sprite, and launchers under bin point there.
SPRITE_HOME="$PREFIX/opt/sprite"

# A source copy taken from a developer tree may carry the staging links
# install and object-root.  They point outside the build; drop them.
for link in install object-root; do
  if [ -L "$link" ]; then
    rm -f "$link"
  fi
done

# The precompiled header of the prebuild step goes to a cache directory in
# the build tree: the tree under $PREFIX lies in a conda prefix, so the C++
# backend writes the header under $XDG_CACHE_HOME/sprite (see
# config.cxx_pch_root), and nothing of the build reaches the home directory
# of the user.
export XDG_CACHE_HOME="$SRC_DIR/cache"

# Paths of the build tree must not reach the package.  The compilers record
# the names of headers in assertions; map the tree to a relative name.
export CFLAGS="${CFLAGS:-} -ffile-prefix-map=$SRC_DIR=."
export CXXFLAGS="${CXXFLAGS:-} -ffile-prefix-map=$SRC_DIR=."

# No PAKCS: the front end comes from the package curry-frontend, and the
# pinned release names the intermediate directories.  No icurry, and no
# ccache: the build runs once, and a ccache found on the build machine
# would otherwise reach Make.config.  make runs the jobs conda-build grants
# (CPU_COUNT); the Makefiles order the sub-makes, so a parallel build is
# safe.  The C++ backend is the default of the package (the default of
# configure, passed here so that the recipe says so).  The tool links that
# this writes are replaced below.  Sprite writes compact JSON itself; no jq.
"$PYTHON" ./configure \
  --with-python="$PYTHON" \
  --with-cc="$CC" \
  --with-cxx="$CXX" \
  --with-cxx-postinstall="$CXX" \
  --with-ccache='' \
  --with-pakcs='' \
  --with-curry-frontend="$PREFIX/bin/pakcs-frontend" \
  --with-icurry='' \
  --with-default-backend=cxx \
  --jobs "${CPU_COUNT:-1}"

# make install builds the C++ runtime (libcyrt) and the extension module,
# copies the Python package, the Curry library with its committed .icy and
# .json.z files, the headers, and the sysconfig files.  It then runs the
# front end over the library, so the package holds the FlatCurry interfaces,
# and compiles the library for both backends (the prebuild step of
# curry/Makefile), so the package holds the generated Python, the bytecode
# caches, and the shared objects of every module Sprite can compile.  The
# first program a user runs compiles nothing of the library.
make install PREFIX="$SPRITE_HOME"

# The static archive names its members by their paths in the build tree
# (ar -P), and nothing uses it at run time: the backend links the shared
# library.  Leave it out of the package.
rm -f "$SPRITE_HOME/lib/libcyrt.a"

# The prebuild step precompiled cyrt/cyrt.hpp for the compiler of the build
# (a member of about 70 MB, named after that compiler).  The tree lies in a
# conda prefix, so the C++ backend put the member into the cache directory
# named above, not into the tree (config.cxx_pch_root).  The compiler of
# the environment cannot use it anyway; the C++ backend builds its own
# member on the first compile, in the cache directory of the user.
test ! -e "$SPRITE_HOME/include/cyrt/cyrt.hpp.gch"

# make writes tools/ as absolute links into the build environments.  Replace
# them with relative links into the prefix.  The C++ compiler gets a wrapper
# that picks the compiler at run time: SPRITE_CXX when set, else the
# compiler of the environment.  An ambient CXX counts only when it names a
# file of the environment, so that the compiler of another environment or
# of the system does not compile against the headers and the runtime
# library of this one.  Nothing in the environment sets CXX: cxx-compiler
# brings gxx, which has no activation script.  The here-document is quoted;
# @HOST@ is the one value filled in.
# The version comes from the host Python; PY_VER of conda-build can name
# the Python that runs conda-build instead.
pyver=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
tools="$SPRITE_HOME/tools"
rm -f "$tools"/*
ln -s "../../../bin/python$pyver" "$tools/python"
ln -s ../../../bin/pakcs-frontend "$tools/curry-frontend"
sed "s|@HOST@|$HOST|g" > "$tools/cxx" <<'CXX_EOF'
#!/bin/sh
# The C++ compiler for the code that Sprite generates at run time.  The
# generated code is compiled against the headers under opt/sprite/include
# and linked against opt/sprite/lib/libcyrt.so of this environment, so the
# compiler is the one of this environment, bin/@HOST@-g++, unless
# SPRITE_CXX names another.  An ambient CXX counts only when it names a
# file of this environment.  The installed headers of Sprite need no
# header of the environment (the runtime uses the C++17 standard library
# alone), so the environment need not be activated.
here=$(dirname "$(readlink -f "$0")")
prefix=$(cd "$here/../../.." && pwd -P)
cxx="$prefix/bin/@HOST@-g++"
if [ -n "${SPRITE_CXX:-}" ]; then
  cxx=$SPRITE_CXX
elif [ -n "${CXX:-}" ]; then
  case $CXX in
    */*) found=$CXX ;;
    *) found=$(command -v "$CXX" 2>/dev/null) || found= ;;
  esac
  if [ -n "$found" ] && [ -f "$found" ]; then
    found=$(cd "$(dirname "$found")" && pwd -P)/$(basename "$found")
    case $found in
      "$prefix"/*) cxx=$found ;;
    esac
  fi
fi
exec "$cxx" "$@"
CXX_EOF
chmod 755 "$tools/cxx"

# The launchers.  Each one sets SPRITE_HOME from its own location and runs
# the script of the same name in the tree.  The location is the real path
# of the launcher, so a link to the launcher from another directory works.
mkdir -p "$PREFIX/bin"
for name in sprite-exec sprite-make; do
  cat > "$PREFIX/bin/$name" <<LAUNCHER_EOF
#!/bin/sh
# Runs $name from the Sprite tree under opt/sprite.
here=\$(dirname "\$(readlink -f "\$0")")
SPRITE_HOME=\$(cd "\$here/../opt/sprite" && pwd)
export SPRITE_HOME
exec "\$SPRITE_HOME/bin/$name" "\$@"
LAUNCHER_EOF
  chmod 755 "$PREFIX/bin/$name"
done

# import curry works in the Python of the environment: a .pth file adds the
# package directory to sys.path.  The package finds its home by itself, and
# the extension module finds libcyrt.so through its run path.
echo "../../../opt/sprite/python" > "$SP_DIR/sprite.pth"

# A check of the tree as the package will install it: compile a module that
# imports every library module through the relative tool links written
# above.  The front end reads the installed interfaces (it rewrites a stale
# one), and the translation to ICurry runs inside the build environment.
# The module is compiled in a scratch directory; nothing is written into
# the tree.
export SPRITE_HOME PYTHONDONTWRITEBYTECODE=1
warm=$(mktemp -d)
{
  for module in $(cat "$SPRITE_HOME/sysconfig/currylib_module_names"); do
    if [ "$module" != Prelude ]; then
      echo "import qualified $module"
    fi
  done
  printf 'main :: Int\nmain = 0\n'
} > "$warm/Warm.curry"
"$SPRITE_HOME/bin/sprite-make" --icy "$warm/Warm.curry"
subdir=$(cat "$SPRITE_HOME/sysconfig/frontend_subdir")
test -s "$SPRITE_HOME/curry/.curry/$subdir/Prelude.fcy"
test -s "$SPRITE_HOME/curry/.curry/$subdir/Prelude.fint"
rm -rf "$warm"
