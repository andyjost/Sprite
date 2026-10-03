#!/bin/bash
# Builds Sprite into the conda prefix.  conda-build sets PREFIX, SRC_DIR,
# PYTHON, SP_DIR, CC, CXX, and HOST.  See ../README.md.
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

# configure looks for the Boost headers under /usr.  BOOST names them.
export BOOST="$PREFIX/include/boost"

# Paths of the build tree must not reach the package.  The compilers record
# the names of headers in assertions; map the tree to a relative name.
export CFLAGS="${CFLAGS:-} -ffile-prefix-map=$SRC_DIR=."
export CXXFLAGS="${CXXFLAGS:-} -ffile-prefix-map=$SRC_DIR=."

# No PAKCS: the front end comes from the package curry-frontend, and the
# pinned release names the intermediate directories.  No icurry.  The tool
# links that this writes are replaced below.
"$PYTHON" ./configure \
  --with-python="$PYTHON" \
  --with-cc="$CC" \
  --with-cxx="$CXX" \
  --with-cxx-postinstall="$CXX" \
  --with-pakcs='' \
  --with-curry-frontend="$PREFIX/bin/pakcs-frontend" \
  --with-icurry='' \
  --with-jq="$PREFIX/bin/jq"

# Serial: the recursive Makefiles link libcyrt.so from two places (the cyrt
# tree and the extension module), which races under make -j.
make install PREFIX="$SPRITE_HOME"

# The static archive names its members by their paths in the build tree
# (ar -P), and nothing uses it at run time: the backend links the shared
# library.  Leave it out of the package.
rm -f "$SPRITE_HOME/lib/libcyrt.a"

# make writes tools/ as absolute links into the build environments.  Replace
# them with relative links into the prefix.  The C++ compiler gets a wrapper
# that resolves the compiler at run time.
# The version comes from the host Python; PY_VER of conda-build can name
# the Python that runs conda-build instead.
pyver=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
tools="$SPRITE_HOME/tools"
rm -f "$tools"/*
ln -s "../../../bin/python$pyver" "$tools/python"
ln -s ../../../bin/jq "$tools/jq"
ln -s ../../../bin/pakcs-frontend "$tools/curry-frontend"
cat > "$tools/cxx" <<CXX_EOF
#!/bin/sh
# The C++ compiler for the code that Sprite generates at run time.
# SPRITE_CXX names it; else CXX, which the activation script of the compiler
# package sets; else the compiler of this environment.  The include
# directory of the environment holds the Boost headers that the installed
# headers of Sprite need; the activation script adds it too, this adds it
# when the environment is not activated.
here=\$(cd "\$(dirname "\$0")" && pwd)
default="\$here/../../../bin/$HOST-g++"
exec "\${SPRITE_CXX:-\${CXX:-\$default}}" -isystem "\$here/../../../include" "\$@"
CXX_EOF
chmod 755 "$tools/cxx"

# The launchers.  Each one sets SPRITE_HOME from its own location and runs
# the script of the same name in the tree.
mkdir -p "$PREFIX/bin"
for name in sprite-exec sprite-make; do
  cat > "$PREFIX/bin/$name" <<LAUNCHER_EOF
#!/bin/sh
# Runs $name from the Sprite tree under opt/sprite.
here=\$(cd "\$(dirname "\$0")" && pwd)
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

# The front end writes the FlatCurry of a library module the first time a
# program imports it.  Compile a module that imports every library module
# now, so that the package holds those files and the tree is not written at
# run time for them.  This also runs the route from Curry to ICurry inside
# the build environment.
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
