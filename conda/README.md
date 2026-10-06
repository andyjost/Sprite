Conda recipes
=============

This directory holds the recipes of two conda packages for Sprite on
linux-64.  Nothing here is published.  The recipes are written for
conda-build.  The layout they produce is described below, so that a port to
rattler-build is straightforward.

Two recipes
-----------

`recipe/` builds the package `sprite` from this repository.  `curry-frontend/`
repackages the Curry front end from the PAKCS binary distribution.  Sprite
needs the front end at run time, so `sprite` depends on `curry-frontend`.
The two packages are separate because they have different licenses and
origins, and because the front end changes with PAKCS, not with Sprite.

Each recipe directory holds `meta.yaml`, `build.sh`, and a
`conda_build_config.yaml`.  The last file sets the two variant keys that
`{{ stdlib("c") }}` needs, `c_stdlib` and `c_stdlib_version`.  The one of
`recipe/` also pins the compiler of the build (see "The compiler" below).
conda-forge supplies those keys through its pinning file.  A build outside
conda-forge needs them in the recipe.

### `recipe/`: the package `sprite`

Source: the repository (`path: ../..`).  The pybind11 submodule under
`extern/pybind11` must be present.

Build (`build.sh`):

1. `configure` runs without PAKCS (`--with-pakcs ''`), without icurry, and
   without ccache.  The front end is `$PREFIX/bin/pakcs-frontend` from the
   host dependency `curry-frontend`.  Without PAKCS, `configure` uses the
   pinned release name and version (`pakcs`, `3.4.1`) for the intermediate
   directories (`.curry/pakcs-3.4.1`, `.curry/sprite-pakcs-3.4.1`) and for
   the front-end flags, so the committed ICurry files stay valid.  `--jobs`
   takes the job count that conda-build grants (`CPU_COUNT`); the Makefiles
   order the sub-makes, so the parallel build is safe.
2. `make install PREFIX=$PREFIX/opt/sprite` builds the C++ runtime
   (`libcyrt`) and the pybind11 extension module, and copies the Python
   package, the Curry library with its committed `.icy` and `.json.z` files,
   the headers, and the sysconfig files.  It then runs the front end over
   the library, which writes the FlatCurry interfaces under
   `opt/sprite/curry/.curry/pakcs-3.4.1/`, and compiles the library for both
   backends (the `prebuild` step of `curry/Makefile`): the ICurry and the
   JSON of every module, and the generated Python, its bytecode cache, and
   the shared object of every module Sprite can compile.  The tree keeps the
   layout of a staged install.  It sits under `opt/sprite` because its `bin/`
   holds the links `python` and `coverage`, which must not replace the ones
   of the environment.
3. The prebuild step compiles with `tools/cxx`, and that step drops the
   compiler flags of the environment, where the activation script of the
   conda compiler put the include directory of the host environment.  So
   `--with-cxx-postinstall` names a small wrapper in the build tree that
   runs the compiler of the build with `-isystem $PREFIX/include`, where the
   Boost headers are.  Without it the first module fails on
   `boost/utility.hpp`.
4. Two build products stay out of the package.  The static archive
   `libcyrt.a` names its members by their build paths, and nothing uses it
   at run time.  The precompiled header `include/cyrt/cyrt.hpp.gch/`, which
   the prebuild step wrote for the compiler of the build, is about 70 MB and
   serves that compiler only; the C++ backend builds one for the compiler of
   the environment on its first compile.
5. The `tools/` links that `make` writes are absolute paths into the build
   environments.  `build.sh` replaces them: `python` and `curry-frontend`
   become relative links into `$PREFIX/bin`; `cxx` becomes a wrapper script
   that resolves the C++ compiler at run time (see "The compiler").
6. `$PREFIX/bin/sprite-exec` and `$PREFIX/bin/sprite-make` are launchers.
   Each one sets `SPRITE_HOME` from its own location and runs the script of
   the same name under `opt/sprite/bin`.
7. `sprite.pth` in `site-packages` adds `opt/sprite/python` to `sys.path`, so
   `import curry` works in the Python of the environment.  The package finds
   `SPRITE_HOME` from its own location when the variable is not set, and the
   extension module finds `libcyrt.so` through a run path relative to itself
   (`src/python/Make.include`), so no activation script is needed.
8. A check of the finished tree: `sprite-make --icy` compiles a module that
   imports every library module, in a scratch directory, through the
   relative tool links.  The front end reads the installed interfaces and
   rewrites a stale one, and the translation to ICurry runs inside the build
   environment.

Relocation.  The compiled library modules name the build prefix: the shared
objects name the modules they import by absolute path (their `NEEDED`
entries, written by `curry.backends.cxx.toolchain.Cpp2So`), and the
generated Python and C++ files name the Curry source of their module.
conda-build finds the prefix in them and lists them in `info/has_prefix`,
39 files: 13 shared objects as binary, 13 `.py` and 13 `.cpp` as text.
conda writes the prefix of the environment into them at install time.
`meta.yaml` spells out `detect_binary_files_with_prefix`, the default on
Linux, because the package depends on it.  Nothing else in the package
names the build directory or the build prefix: the links and launchers are
relative, the sysconfig values name no prefix (`ld_interpreter_path` is a
path, the dynamic loader `/lib64/ld-linux-x86-64.so.2`; see open question
13), and `-ffile-prefix-map` keeps the source directory out of the runtime
binaries.  Three consequences remain.
The bytecode caches (`__pycache__`) record the build prefix as the source
path of their modules, as the `.pyc` files of every conda package do;
Python does not use that path to find or to validate a module.  The
bytecode caches of the 13 generated library modules are stale after the
install, because the text replacement changed their `.py` files: Python
compiles such a module again on its first import and writes the cache
again when it can (see open question 3).  And the C++ backend compiled a
library module again on its first import until issue #66 was fixed.  The
toolchain starts a module from the newest file of its chain (`.curry`,
`.icy`, `.json.z`, `.cpp`, `.so`; `curry.toolchain._findcurry` with
`filesys.newest`).  It compared change times, and conda gives the `.cpp`,
`.py`, and `.so` it rewrote their final change times in an arbitrary
order, about two seconds after the write.  When the `.cpp` of a module
ended newer than its `.so`, the first import compiled the module again and
wrote the shared object and its stamp into `opt/sprite`, although the
ABI stamp of the shipped object was accepted.  Observed on 2026-10-05: the
environment made from the build of record compiled Prelude, Data.List,
and Data.Maybe again on its first C++ run (34 s instead of 3 s), and
later Data.Char on its first import, while it kept Data.Either, whose
`.so` had the later change time; the environment made from the build
before it kept Prelude, Data.List, and Data.Maybe.  The toolchain now
compares modification times (issue #66).  The shipped object is then kept
when the `.cpp` of the module keeps a modification time before the one of
its `.so`: the rewrite of the install of record left the modification
times in the order of the chain (`.cpp` before `.py` before `.so`, the
sorted order of the paths).  An installer that rewrites the text files
after the binaries would give the `.cpp` the later time, and the first
import would compile the module again.  No package was rebuilt and
installed under the new rule yet; the first install should confirm the
expectation.  See open question 3.

Dependencies:

| Kind  | Package                 | Why                                                     |
|-------|-------------------------|---------------------------------------------------------|
| build | `{{ compiler('c') }}`, `{{ compiler('cxx') }}`, `{{ stdlib('c') }}`, `make` | the C++ runtime and the extension |
| host  | `python 3.14.*`         | the extension module and the Python package             |
| host  | `libboost-headers`      | `boost/integer`, `boost/io`, `boost/pool`, `boost/preprocessor`, `boost/utility`; headers only |
| host  | `curry-frontend 2.0.0.*` | `configure` checks it; `make install` runs it over the library |
| run   | `python 3.14.*`         | `python_abi` pins the CPython 3.14 ABI                  |
| run   | `curry-frontend 2.0.0.*` | Curry to FlatCurry; it brings `gmp` (libgmp)           |
| run   | `cxx-compiler`          | the C++ backend compiles generated code at run time     |
| run   | `libboost-headers`      | the installed headers of Sprite include Boost           |

`libgmp` is a dependency of the front end binary, not of Sprite, so it is a
run dependency of `curry-frontend` (the package `gmp`) and reaches the
environment through it.  The run exports of the build compiler add
`libgcc >=15` and `libstdcxx >=15`, and `{{ stdlib('c') }}` adds
`__glibc >=2.17`.

The compiler.  The C++ backend runs `tools/cxx` for every module it
compiles.  In the package that is a wrapper: it runs `SPRITE_CXX` when set,
else the compiler of the environment, `bin/<host>-g++`.  An ambient `CXX`
counts only when it names a file under the prefix of the environment (the
wrapper resolves a bare name through `PATH` and compares physical paths).
A compiler of another environment or of the system is not used: the
generated code must see the headers and the runtime library of this
environment.  Nothing in the environment sets `CXX`; `cxx-compiler` 2.0.0
brings `gxx`, which has no activation script.  The wrapper adds `-isystem`
for the include directory of the environment, where the Boost headers are,
so the environment need not be activated.  `cxx-compiler` 2.0.0 brings GCC
15 with the conda-forge sysroot, so `conda_build_config.yaml` pins the
compiler of the build to GCC 15 as well:
the generated code is compiled against the headers under
`opt/sprite/include` and linked against `opt/sprite/lib/libcyrt.so`, and one
major version keeps one libstdc++ on both sides.  Move the pin together with
`cxx-compiler`.  The compiled library modules do not depend on the compiler
version: their ABI stamps (`.so.abi`) digest the runtime headers and the
flavor flags, so the ABI check of the C++ backend accepts them (the change
times of the install can still make it compile one again; see
"Relocation").

Tests (`meta.yaml`): the launchers, `import curry`, and one program on each
backend through `sprite-exec` and through `python -m curry`.  The library
comes compiled.  The C++ backend is the default: under its tiered mode a
short program runs interpreted and its background compile is cancelled at
exit, so the two default-backend tests check the value alone.  A third test
compiles the program with `sprite-make --so` and checks that the shared
object and the ABI stamp exist beside it (`.curry/sprite-pakcs-3.4.1/
Smoke.so` and `Smoke.so.abi`), which shows that the compiler of the
environment works; it also builds the precompiled header of the runtime
for that compiler.  The two Python-backend tests select the backend with
`SPRITE_INTERPRETER_FLAGS=backend:py`.  The test step of the build of
2026-10-05, with the Python backend as the default of that tree, took 8 s;
the recipe of this text has not been built yet.

Package contents (the build of 2026-10-05): 682 files, 2.2 MB compressed,
19 MB installed.

| Directory                        | Files | Size   | Contents                                                   |
|----------------------------------|------:|-------:|------------------------------------------------------------|
| `bin/`                           |     2 |        | the launchers `sprite-exec` and `sprite-make`              |
| `lib/python3.14/site-packages/`  |     1 |        | `sprite.pth`                                               |
| `opt/sprite/python/`             |   335 | 3.8 MB | the package `curry`: 167 modules, their bytecode, the extension module |
| `opt/sprite/curry/`              |   282 |  14 MB | 22 sources with LICENSE and NOTICE; FlatCurry, interfaces, ICurry and JSON of every module; Python, bytecode, C++, shared object, and ABI stamp of the 13 compiled modules |
| `opt/sprite/include/`            |    38 | 244 KB | the runtime headers                                        |
| `opt/sprite/lib/`                |     1 | 604 KB | `libcyrt.so`                                               |
| `opt/sprite/sysconfig/`          |    15 |        | the settings Sprite reads at run time                      |
| `opt/sprite/bin/`, `opt/sprite/tools/` | 8 |     | the scripts of the tree; the links `python` and `curry-frontend`, the wrapper `cxx` |

The dependencies of the package are `__glibc >=2.17,<3.0.a0`,
`curry-frontend 2.0.0.*`, `cxx-compiler`, `libboost-headers`, `libgcc >=15`,
`libstdcxx >=15`, `python >=3.14,<3.15.0a0`, and `python_abi 3.14.* *_cp314`.
An environment with the package and its dependencies takes 1.4 GB, most of
it the compiler, its sysroot, and Python.

conda-build warns that `python` is in `requirements/run` "but not used".
Its check looks for linked libraries; the scripts use it.  The warning is
harmless.

### `curry-frontend/`: the package `curry-frontend`

Source: `pakcs-3.4.1-amd64-Linux.tar.gz` from curry-lang.org, whose SHA-256
is in `meta.yaml`.  `build.sh` installs `bin/pakcs-frontend` (an ELF binary,
9.2 MB, linked against libgmp.so.10 and the C library) and the link
`bin/curry-frontend`.  conda-build sets the run path of the binary to the
`lib` directory of the prefix, where the package `gmp` installs libgmp.
The package is 1.5 MB and holds the two files.  Its dependencies are
`gmp >=6.3.0,<7.0a0` and `__glibc >=2.17,<3.0.a0`; the binary itself needs
symbols up to GLIBC_2.14.

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

Neither recipe is on a channel.  The build needs conda-build, a package
cache, a build root, and an output folder, which becomes the local channel.
Plan about 2 GB for the build root (the build, host, and test environments
of a build stay there until `conda build purge`) and about 3.5 GB for the
package cache.

    conda create -p /path/to/build-env --override-channels -c conda-forge conda-build
    export CONDA_PKGS_DIRS=/path/to/pkgs     # optional: a writable cache
    croot=/path/to/build-root
    channel=/path/to/channel
    cd /path/to/Sprite
    conda build conda/curry-frontend --croot $croot --output-folder $channel \
        --override-channels -c conda-forge
    conda build conda/recipe --croot $croot --output-folder $channel \
        --override-channels -c file://$channel -c conda-forge

Run conda-build from a shell in which no conda environment is active and no
compiler variable is set (`CC`, `CXX`, `CFLAGS`, `CXXFLAGS`, `LDFLAGS`).  The
test step activates the test environment, which first deactivates the
active one and runs its deactivation scripts; and the activation scripts of
a conda compiler in the shell add their flags and include directories to
the build.  The simple way is
`env -i PATH=/usr/bin:/bin HOME=$HOME conda build ...`, with the proxy
variables added when the network needs them.  conda-build reads `CPU_COUNT`
from the environment for the job count of make.  `/tmp` must be writable:
the activation scripts of the conda-forge compilers write
`/tmp/old-env-<pid>.txt` during a build.

The first build downloads the PAKCS archive (4 MB).  To build from a copy
that is already on disk, put the copy into the source cache under the name
conda-build uses, the file name with the first ten characters of the hash:

    mkdir -p $croot/src_cache
    cp pakcs-3.4.1-amd64-Linux.tar.gz $croot/src_cache/pakcs-3.4.1-amd64-Linux_d17d8b3c30.tar.gz

The `curry-frontend` build takes about two minutes.  The `sprite` build took
4 min 19 s from the creation of its environments to the end of its tests
with `CPU_COUNT=4` and a warm package cache; most of that time is the C++
runtime and the 13 library modules.

Testing the packages
--------------------

An environment with both packages, from the local channel:

    conda create -p /path/to/env --override-channels -c file://$channel -c conda-forge sprite python=3.14

Then, from a directory outside the repository and without activation of
the environment, with a program `Smoke.curry` whose goal `main` has several
values:

    /path/to/env/bin/sprite-exec Smoke.curry
    SPRITE_INTERPRETER_FLAGS=backend:py /path/to/env/bin/sprite-exec Smoke.curry
    /path/to/env/bin/python -m curry Smoke.curry
    /path/to/env/bin/python -c 'import curry; from curry.lib import Prelude; print(next(curry.eval(curry.expr(Prelude.length, [1, 2, 3]))))'

The times of that test on 2026-10-05, each command in a scrubbed
environment (`env -i`, no `SPRITE_HOME`, no `CXX`), the first run in a
fresh directory and the second run beside its products.  The Python
backend was the default of that build, and the C++ backend compiled the
program before it ran (the interpreter flag `interpret` was `off`); under
the tiered default of today a short program ends interpreted, before its
compile:

| Command                                   | Backend | First run | Second run |
|-------------------------------------------|---------|----------:|-----------:|
| `sprite-exec Smoke.curry`                 | py      |    1.05 s |     0.21 s |
| `sprite-exec Smoke.curry`                 | cxx     |   34.48 s |     0.26 s |
| `python -m curry Smoke.curry`             | py      |    0.71 s |     0.18 s |
| `python -m curry Smoke.curry`             | cxx     |    1.28 s |     0.24 s |
| `import curry`, two Prelude calls         | py      |    0.78 s |     0.80 s |
| `import curry`, two Prelude calls         | cxx     |    1.13 s |     1.06 s |

The first run on the Python backend runs the front end and the translation
to ICurry and writes the Python of the program; the first run on the C++
backend also builds the precompiled header of the runtime (about two
seconds) and compiles the program.  In this run it also compiled Prelude,
Data.List, and Data.Maybe again (see "Relocation"); the same test on the
build before it, whose install kept the three modules, took 3.07 s.  The
`python -m curry` runs on the C++
backend came after that and found the header built, so their first run
compiled the program only.  The Python test compiles one of its two
expressions from Curry text, which runs the front end on each run.
All products of the program go to `.curry/` beside it.  Three things were
written under `opt/sprite` of the environment during the runs: the
precompiled header, the bytecode caches of the library modules the program
imported, and the shared objects and ABI stamps of the three modules named
above (see "Relocation").

The unit tests of the recipe files, `tests/unit_conda.py`, run with the
test drivers of the repository.  They check the recipe files and the build
options the recipe relies on, not a build.

Status
------

Both recipes were built on 2026-10-05 with conda-build 26.9.1 (conda
26.9.1, Python 3.13) on linux-64, from the working tree of the branch and
from the PAKCS archive that conda-build downloaded.  Both packages passed
their tests.  The environment made from the two packages ran the test of
the section above on both backends without activation: `sprite-exec`,
`python -m curry`, and `import curry` with Prelude calls from the Python of
the environment, with no `SPRITE_HOME` set.  The ICurry oracle of
`tests/README` was not run against this build.

Decisions taken for this build
------------------------------

These choices make the package install and run today.  Each one is open to
the owner; the next section gives a recommendation for each.

1. The front end is a separate package, `curry-frontend`, repackaged from
   the PAKCS binary distribution.  It is neither bundled into `sprite` nor
   downloaded at run time.
2. Both backends are in one package.  The C++ backend is the default
   (`DEFAULT_BACKEND` in `Make.config`; `build.sh` passes
   `--with-default-backend=cxx` to `configure`, which is also its default),
   and `cxx-compiler` is a run dependency, so the C++ backend compiles the
   generated code after one `conda create`.  Without the compiler the C++
   backend runs every module interpreted and prints one notice per process
   (the page "Installing and running without a C++ compiler" of the
   documentation).
3. The front end is pinned exactly: `curry-frontend 2.0.0.*`, the front end
   of PAKCS 3.4.1.
4. The compiler of the build is GCC 15, the major version that
   `cxx-compiler` 2.0.0 brings at run time.
5. The library is compiled into the package for both backends.  The
   precompiled header of the runtime is not; the C++ backend writes it on
   its first compile.

Open questions
--------------

Resolve these before anything is published.  The license question of the
first scaffold is closed: `LICENSE` at the root of the repository is the
BSD 3-Clause license of Sprite, and the package ships it with the notices
of the Curry library (`curry/lib/LICENSE`, `curry/lib/NOTICE`) and of
pybind11.

1. The front end.  Keep the separate package.  The binary has its own
   license and origin, it moves with PAKCS and not with Sprite, and a
   package that downloads at run time is not acceptable on conda-forge.  To
   publish it, a feedstock `curry-frontend` is the first step; a second
   platform needs a build of the front end from source (GHC, Stack resolver
   lts-16.9).
2. The compiler at run time.  Keep `cxx-compiler` as a run dependency for
   now: the first user must get compiled code from one command.  Later,
   split the package: `sprite` with the C++ runtime, its ICurry interpreter
   (the interpreter flag `interpret`) and the compiled library objects,
   which runs without a compiler, and a metapackage `sprite-cxx` that adds
   `cxx-compiler` for the background compile of the user's modules.  The
   split is a follow-up of the packaging issue #1; stage 2 of issue #82
   (the compiler-free mode) documented the behaviour and did not split the
   package.  One fact for the split: the ABI stamp of a compiled module
   (`.so.abi`) digests the real path of the installation prefix (issue #82,
   the audit's finding on objects under another prefix), so an environment
   whose prefix differs from the build prefix finds the shipped library
   objects stale.  With `cxx-compiler` the first import compiles the
   library again into `opt/sprite`; without it, every module runs
   interpreted and one notice says so.  A probe of 2026-10-06 with an
   installation served under another path showed both; a conda build under
   the new rule has not been tested.  A system compiler should stay out:
   the generated code must see the libstdc++ headers of a compiler that
   matches the runtime library of the environment.
3. Writes into the package at run time.  The library comes compiled, so a
   program writes its own products beside its source.  Three writes remain
   under `opt/sprite`.  The first C++ compile writes the precompiled header
   under `opt/sprite/include/cyrt/cyrt.hpp.gch/` (about 70 MB); conda does
   not track it, it stays behind on removal, and a read-only environment
   gets a warning and slower compiles (`SPRITE_CXX_PCH_ROOT` names another
   directory).  Recommendation: let the C++ backend put the header into a
   per-user cache directory (`$XDG_CACHE_HOME/sprite`, else
   `~/.cache/sprite`) by default when the installed include directory is
   not writable or lies in a conda prefix, and keep the variable as the
   override.  The first import of a library module on the Python backend
   writes its bytecode cache again, because the prefix replacement of conda
   changed the generated `.py` file.  Recommendation: let the code
   generators write the source path of a module relative to `SPRITE_HOME`,
   or leave it to the loader; then the generated files carry no prefix,
   `info/has_prefix` shrinks to the 13 shared objects, and the shipped
   bytecode stays valid.  The third write was the shared object of a
   library module whose `.cpp` got a later change time than its `.so` at
   install time (see "Relocation"): the first import on the C++ backend
   compiled the module again, Prelude included (about 25 s).  Issue #66
   changed the measure: the toolchain compares modification times instead
   of change times, and the rewrite of this install left those in chain
   order, so the write is expected to be gone; an install under the new
   rule has not confirmed it yet (see "Relocation").  The recommendation
   above still helps here: with no prefix in the generated files, conda
   rewrites the `.so` alone, and the order of the chain no longer depends
   on the order in which the installer rewrites the files.
4. The Python backend.  The C++ backend is the default of the repository
   since issue #82; `configure --with-default-backend` sets
   `DEFAULT_BACKEND`, and `build.sh` passes `cxx`.  Keep both backends in
   one package until the Python backend is removed (the removal gate of
   issue #82); the Python backend is selected with the interpreter flag
   `backend:py`.
5. The pin of PAKCS 3.4.1.  Keep the exact pin: the committed ICurry files
   and the oracle depend on the FlatCurry of front end 2.0.0.  When a new
   PAKCS is adopted, `curry-frontend` gets a new version and the pin in
   `recipe/meta.yaml` moves with `PINNED_FRONTEND_VERSION` in `configure`.
   One source of truth for the two would be better.
6. The compiler pin.  `conda_build_config.yaml` pins GCC 15 for the build.
   On conda-forge the global pinning sets the compiler version and the
   feedstock drops this file; the run dependency `cxx-compiler` then gives
   whatever major version conda-forge ships, and the generated code may be
   compiled by a newer compiler than the runtime.  That is the normal
   libstdc++ case (a newer compiler with a runtime library at least as new
   as the build's, which the run export keeps), but it is untested here.
   Recommendation: test the package once with a compiler one major version
   newer than the build before anything is published.  Two other options
   tie the two sides.  A run dependency or a `run_constrained` entry
   `gxx {{ cxx_compiler_version }}.*` makes the compiler of the environment
   the compiler of the build; today `cxx-compiler` 2.0.0 itself depends on
   `gxx 15.*`, and a later `cxx-compiler` moves on without this recipe
   noticing.  Or drop the local pin and take the compiler of the pinning
   file on both sides.  Decide before publication.
7. macOS.  Sprite's Makefiles use GNU make, `realpath`, `flock`, and GNU
   linker flags (`--whole-archive`, `--no-undefined`, `-z undefs`).  The front
   end binary comes from the Linux distribution of PAKCS only; macOS needs
   the PAKCS or KiCS2 distribution for macOS, or a build of the front end
   from source with GHC (Stack resolver lts-16.9).  The run path of the
   extension module uses `$ORIGIN`, which is `@loader_path` on macOS.
8. Windows.  Not planned: the build system is make and bash, the C++
   backend assumes ELF shared objects and `dlopen`, and the front end has no
   Windows binary.
9. PAKCS.  The package has no PAKCS, so `tests/oracle` cannot run the
   functional tests against it.  The unit tests run without PAKCS.
10. Versions.  `recipe/meta.yaml` carries the version by hand; keep it equal
    to the `VERSION` file.  conda-build can read the file at render time:
    `{% set version = load_file_regex(load_file="../../VERSION",
    regex_pattern="(\S+)", from_recipe_dir=True).group(1) %}`.
11. The source of the Sprite recipe is the working tree, with whatever
    untracked files it holds.  A release tarball from GitHub lacks the
    pybind11 submodule.  A published recipe should list two `url` sources,
    the release tarball and the pybind11 tarball with `folder:
    extern/pybind11`, or add the conda-forge package `pybind11` to the host
    requirements, whose headers the compiler finds under `$PREFIX/include`.
12. Pip.  A wheel of the Python backend (roadmap issue #1) needs the front
    end on the user's machine; the conda package solves that through
    `curry-frontend`.  A wheel that bundles the front end binary would carry
    a 9 MB binary per wheel and the PAKCS license.  Decide the channel of
    the conda packages first.
13. `ld_interpreter_path`.  The sysconfig value is a fixed file of the
    repository (`src/export/sysconfig/ld_interpreter_path.var`): the
    dynamic loader of glibc on x86-64 Linux, `/lib64/ld-linux-x86-64.so.2`.
    The C++ backend writes it into the `.interp` section of the shared
    object of a module with a `main` goal
    (`curry.backends.cxx.compiler._generate_main`).  It is the one
    sysconfig value that names a path of the machine, and the one
    assumption the package makes about the machine outside the
    environment: a second platform, or a libc other than glibc, needs
    another value.  Recommendation: let `configure` read the `PT_INTERP`
    of the Python of the environment, or drop the section if nothing runs
    the shared objects directly.
14. The sysroot at run time.  The build compiles against the conda-forge
    sysroot 2.17 (`c_stdlib_version`).  The C++ backend compiles generated
    code against the sysroot of the environment, which the recipe does not
    pin: the test environment of 2026-10-05 got `sysroot_linux-64 2.39`
    (that package depends on `__glibc >=2.39`, so a machine with an older
    glibc gets an older sysroot).  The generated code thus sees the glibc
    headers of a newer sysroot than the runtime library was built with.
    That worked here and is the normal case for glibc, but it is untested
    on another machine.  A run dependency `sysroot_linux-64 2.17.*` would
    give the generated code the headers of the build everywhere.  Decide
    before publication.
15. The notices of the front end.  `pakcs-frontend` is a GHC executable:
    its Haskell libraries are linked into it statically, and the strings of
    the binary name GHC 8.8.3 and the packages binary, bytestring,
    containers, extra, network-uri, parsec, pretty, process, set-extra,
    time, transformers, and unix, besides curry-frontend itself.  The
    package `curry-frontend` ships the PAKCS license and the front-end
    license only, not the notices of those libraries.  (libgmp is linked
    dynamically and comes from the conda package `gmp` with its own
    notices.)  Before publication, list the libraries of the pinned front
    end from its cabal file and add their license files to `license_file`.
