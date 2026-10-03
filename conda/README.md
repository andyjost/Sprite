Conda recipes
=============

This directory holds the scaffold of a conda package for Sprite on linux-64.
Nothing here is published.  The recipes were written for conda-build; the
layout they produce is described below so that a port to rattler-build is
straightforward.

Two recipes
-----------

`recipe/` builds the package `sprite` from this repository.  `curry-frontend/`
repackages the Curry front end from the PAKCS binary distribution.  Sprite
needs the front end at run time, so `sprite` depends on `curry-frontend`.
The two packages are separate because they have different licenses and
origins, and because the front end changes with PAKCS, not with Sprite.

Each recipe directory holds `meta.yaml`, `build.sh`, and a
`conda_build_config.yaml`.  The last file sets the two variant keys that
`{{ stdlib("c") }}` needs, `c_stdlib` and `c_stdlib_version`.  conda-forge
supplies those keys through its pinning file.  A build outside conda-forge
needs them in the recipe.

### `recipe/`: the package `sprite`

Source: the repository (`path: ../..`).  The pybind11 submodule under
`extern/pybind11` must be present.

Build (`build.sh`):

1. `configure` runs without PAKCS (`--with-pakcs ''`) and without icurry.
   The front end is `$PREFIX/bin/pakcs-frontend` from the host dependency
   `curry-frontend`.  Without PAKCS, `configure` uses the pinned release name
   and version (`pakcs`, `3.4.1`) for the intermediate directories
   (`.curry/pakcs-3.4.1`, `.curry/sprite-pakcs-3.4.1`) and for the front-end
   flags, so the committed ICurry files stay valid.
2. `make install PREFIX=$PREFIX/opt/sprite` builds the C++ runtime
   (`libcyrt`), the pybind11 extension module, copies the Python package, the
   Curry library with its committed `.icy` and `.json.z` files, the headers,
   and the sysconfig files.  The tree keeps the layout of a staged install.
   It sits under `opt/sprite` because its `bin/` holds the links `python` and
   `coverage`, which must not replace the ones of the environment.  make runs
   serially: the recursive Makefiles link `libcyrt.so` from two places, and
   that races under `make -j`.
3. The `tools/` links that `make` writes are absolute paths into the build
   environments.  `build.sh` replaces them: `python`, `jq`, and
   `curry-frontend` become relative links into `$PREFIX/bin`; `cxx` becomes a
   wrapper script that resolves the C++ compiler at run time (see below).
4. `$PREFIX/bin/sprite-exec` and `$PREFIX/bin/sprite-make` are launchers.
   Each one sets `SPRITE_HOME` from its own location and runs the script of
   the same name under `opt/sprite/bin`.
5. `sprite.pth` in `site-packages` adds `opt/sprite/python` to `sys.path`, so
   `import curry` works in the Python of the environment.  The package finds
   `SPRITE_HOME` from its own location when the variable is not set, and the
   extension module finds `libcyrt.so` through a run path relative to itself
   (`src/python/Make.include`), so no activation script is needed.
6. `make install` writes the FlatCurry of the library
   (`opt/sprite/curry/.curry/pakcs-3.4.1/`) with the front end, so it is part
   of the package.  `build.sh` then runs `sprite-make` once over a module that
   imports every library module.  This checks the route from Curry to ICurry
   inside the build environment, and it checks that the installed interfaces
   are current (the front end rewrites a stale one).

Nothing in the package names the build directory or the build prefix.  The
links and launchers are relative, and the sysconfig values hold no paths.
`-ffile-prefix-map` keeps the source directory out of the binaries.  The
static archive `libcyrt.a` is left out, because its member names are build
paths.

Dependencies:

| Kind  | Package                 | Why                                                     |
|-------|-------------------------|---------------------------------------------------------|
| build | `{{ compiler('c') }}`, `{{ compiler('cxx') }}`, `{{ stdlib('c') }}`, `make` | the C++ runtime and the extension |
| host  | `python 3.14.*`         | the extension module and the Python package             |
| host  | `libboost-headers`      | `boost/preprocessor` and `boost/io`, headers only       |
| host  | `jq`, `curry-frontend 2.0.0.*` | `configure` checks them; the front end runs at build time |
| run   | `python 3.14.*`         | `python_abi` pins the CPython 3.14 ABI                  |
| run   | `jq`                    | compacts the JSON that Sprite writes                    |
| run   | `curry-frontend 2.0.0.*` | Curry to FlatCurry; it brings `gmp` (libgmp)           |
| run   | `cxx-compiler`          | the C++ backend compiles generated code at run time     |
| run   | `libboost-headers`      | the installed headers of Sprite include Boost           |

`libgmp` is a dependency of the front end binary, not of Sprite, so it is a
run dependency of `curry-frontend` (the package `gmp`) and reaches the
environment through it.

Tests (`meta.yaml`): the launchers, `import curry`, and one program on each
backend.  The C++ backend test compiles the Prelude with the compiler of
the environment and takes a few minutes.

conda-build warns that `python` and `jq` are in `requirements/run` "but not
used".  Its check looks for linked libraries; both are used by scripts.  The
warnings are harmless.

### `curry-frontend/`: the package `curry-frontend`

Source: `pakcs-3.4.1-amd64-Linux.tar.gz` from curry-lang.org, whose SHA-256
is in `meta.yaml`.  `build.sh` installs `bin/pakcs-frontend` (an ELF binary,
9.2 MB, linked against libgmp.so.10 and the C library) and the link
`bin/curry-frontend`.  conda-build sets the run path of the binary to the
`lib` directory of the prefix, where the package `gmp` installs libgmp.

Notices: `LICENSE` of the PAKCS distribution (the PAKCS license, a three
clause BSD text, Michael Hanus, University of Kiel) and
`LICENSE.curry-frontend`, which is `frontend/LICENSE` of the PAKCS source
distribution (BSD-3-Clause, Wolfgang Lux and Michael Hanus).  A copy of the
second file sits in the recipe directory, so the recipe downloads one
archive.  The version of the package is the version of the front end,
2.0.0; the build string names the PAKCS release.

The test runs `pakcs-frontend --numeric-version`.  A compile test needs a
Prelude, which this package does not carry (`NoImplicitPrelude` makes the
front end fail with an internal error).

Building locally
----------------

Neither recipe is on a channel.  To build both with conda-build:

    export CONDA_PKGS_DIRS=/path/to/a/writable/pkgs/cache   # optional
    croot=/path/to/a/build/root
    conda build --croot $croot --override-channels -c conda-forge conda/curry-frontend
    conda build --croot $croot --override-channels -c $croot -c conda-forge conda/recipe

The first build downloads the PAKCS archive.  To build it from a copy that
is already on disk, put the copy into the source cache under the name
conda-build uses, the file name with the first ten characters of the hash:

    mkdir -p $croot/src_cache
    cp pakcs-3.4.1-amd64-Linux.tar.gz $croot/src_cache/pakcs-3.4.1-amd64-Linux_d17d8b3c30.tar.gz

Then an environment with both packages:

    conda create -p /path/to/env --override-channels -c $croot -c conda-forge sprite
    /path/to/env/bin/sprite-exec examples/Peano.curry

Status
------

Both recipes were built once with conda-build 26.7.1 on linux-64, from the
working tree and from a local copy of the PAKCS archive, and both passed
their tests.  The environment made from the two packages ran `sprite-exec`
and `sprite-make` without activation on both backends, `import curry` from
the Python of the environment without `SPRITE_HOME`, and the ICurry oracle:
every test module with an oracle file (1,183) compiled through the packaged
front end and translation to the same bytes, and the port in the package
reproduced all 1,195 files of the overlay archive.  No file of the package
names the build directory or the build prefix.

Open questions
--------------

Resolve these before anything is published.

1. License.  The repository has no LICENSE file.  conda-forge requires
   `about/license` and `about/license_file`.  Add the license of Sprite, then
   name it in `recipe/meta.yaml`.  The notices of the third-party parts are
   already listed: the Curry library of PAKCS (`curry/lib/LICENSE`,
   `curry/lib/NOTICE`) and pybind11.
2. The compiler at run time.  The C++ backend runs `tools/cxx`.  In the
   package that is a wrapper: it runs `SPRITE_CXX` if set, else `CXX`, which
   the activation script of the compiler package sets, else
   `bin/<host>-g++` of the environment, and it adds `-isystem` for the
   include directory of the environment, where the Boost headers are (the
   installed headers of Sprite include Boost, so `libboost-headers` is a
   run dependency).  `cxx-compiler` pulls in the conda-forge toolchain and
   its sysroot.  The generated code is compiled against the headers under
   `opt/sprite/include` and linked against `opt/sprite/lib/libcyrt.so`; the
   libstdc++ of the run-time compiler must be at least as new as the one
   `libcyrt.so` was built with, which the `libstdcxx` run export of the
   build compiler guarantees.  Open: whether to ship precompiled library
   modules so that the Python backend needs no compiler at all, and whether
   a system compiler should be allowed.
3. Writes into the package at run time.  Sprite writes compiled forms of
   library modules (`.py`, `.cpp`, `.so`) into
   `opt/sprite/curry/**/.curry/sprite-pakcs-3.4.1/` the first time a program
   imports them, and the C++ backend writes its precompiled header into
   `opt/sprite/include/cyrt/cyrt.hpp.gch/`.  conda does not track those
   files.  They are left behind on removal, and a read-only environment
   cannot write them (the precompiled header then falls back to a warning
   and a slower compile; `SPRITE_CXX_PCH_ROOT` names another directory).
   Options: compile the pinned library modules at build time for the Python
   backend, and move the per-user products to a cache directory.
4. macOS.  Sprite's Makefiles use GNU make, `realpath`, `flock`, and GNU
   linker flags (`--whole-archive`, `--no-undefined`, `-z undefs`).  The front
   end binary comes from the Linux distribution of PAKCS only; macOS needs
   the PAKCS or KiCS2 distribution for macOS, or a build of the front end
   from source with GHC (Stack resolver lts-16.9).  The run path of the
   extension module uses `$ORIGIN`, which is `@loader_path` on macOS.
5. Windows.  Not planned: the build system is make and bash, the C++
   backend assumes ELF shared objects and `dlopen`, and the front end has no
   Windows binary.
6. PAKCS.  The package has no PAKCS, so `tests/oracle` cannot run the
   functional tests against it.  The unit tests run without PAKCS.
7. Versions.  `recipe/meta.yaml` carries the version by hand; keep it equal
   to the `VERSION` file.  The front end pin is exact (2.0.0 of PAKCS 3.4.1)
   because the ICurry oracle depends on its output.
8. The source of the Sprite recipe is the working tree.  A release tarball
   from GitHub lacks the pybind11 submodule; a published recipe should use
   `git_url` with the submodule, or add `pybind11` to the host requirements
   and point the include path at it.
9. jq.  Sprite uses jq only to compact JSON.  `configure --with-jq ''`
   leaves it out; the package keeps it as a run dependency so that the
   JSON files match the ones of a developer installation.
