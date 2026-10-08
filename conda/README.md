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
3. The prebuild step compiles with `tools/cxx`, which `make install` links
   to the compiler of the build (`--with-cxx-postinstall="$CXX"`).  The
   step drops the compiler flags of the environment, which does not matter:
   the installed headers of Sprite need no header of the environment since
   the runtime dropped Boost (2026-10-07).  Before that, a wrapper in the
   build tree added `-isystem $PREFIX/include` for the Boost headers.
4. One build product stays out of the package: the static archive
   `libcyrt.a` names its members by their build paths, and nothing uses it
   at run time.  The precompiled header that the prebuild step wrote for
   the compiler of the build (about 70 MB, for that compiler only) never
   enters the tree: the tree lies in a conda prefix, so the C++ backend
   puts the header into the cache directory `$XDG_CACHE_HOME/sprite`
   (`config.cxx_pch_root`), which `build.sh` points into the build tree.
   `build.sh` checks that `include/cyrt/cyrt.hpp.gch` does not exist.
5. The `tools/` links that `make` writes are absolute paths into the build
   environments.  `build.sh` replaces them: `python` and `curry-frontend`
   become relative links into `$PREFIX/bin`; `cxx` becomes a wrapper script
   that resolves the C++ compiler at run time (see "The compiler").
6. `$PREFIX/bin/sprite-exec` and `$PREFIX/bin/sprite-make` are launchers.
   Each one sets `SPRITE_HOME` from the real path of its own location
   (`readlink -f`), so a link to a launcher from another directory works,
   and runs the script of the same name under `opt/sprite/bin`.
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
9. The generated files of the library name their sources relative to the
   installation.  The code generators write `curry/Prelude.curry` for a
   source under `SPRITE_HOME` (`curry.toolchain._filenames.installed_relpath`),
   the generated Python resolves the name against the installation of the
   process when it loads (`curry.config.installed_path`), and the loader of
   the C++ backend resolves the name of the module record the same way.  A
   source outside the installation keeps its absolute path in the generated
   Python; the record of the generated C++ names it relative to the object
   (`../../M.curry`; format 13).  So no generated text file of the package
   holds the build prefix.

Relocation.  One kind of file of the package names the build prefix: the
ABI stamp beside each compiled library module (`.so.abi`, 13 files) names
the real path of the installation as text on its second line (issue #100,
2026-10-07).  conda-build lists the stamps as text entries of
`info/has_prefix` (it finds the prefix in a text file by itself; no line of
`meta.yaml` or `build.sh` is needed) and conda rewrites them at install
time, so the shipped objects count as current in the environment.  The
stamp holds the real path, so the build prefix must be a real path for
conda-build to find it in the stamps (a build root without a link in it).
The shared objects themselves hold no path since format 13 of the generated
code (2026-10-08): each object carries the `SONAME`
`sprite-<module>.so.<format>` and names the modules it imports by their
`SONAME` in its `NEEDED` entries (`curry.backends.cxx.toolchain.Cpp2So`),
and the loader opens the imports of an object before the object, so the
dynamic linker finds each name mapped.  Before format 13 the `NEEDED`
entries named the objects of the imports by absolute path, conda-build
listed the 12 objects with imports in `info/has_prefix` as binary files
(the build of 2026-10-07), and conda patched the paths at install time.
`meta.yaml` keeps `detect_binary_files_with_prefix` spelled out, the default
on Linux, so that a binary file that holds the prefix again shows up in
`info/has_prefix`.  Nothing else in the package names the build directory or
the build prefix: the generated Python and C++ files name their sources
relative to the installation (step 9 above), the links and launchers are relative,
the sysconfig values name no prefix (`ld_interpreter_path` is a path, the
dynamic loader `/lib64/ld-linux-x86-64.so.2`; see open question 13), and
`-ffile-prefix-map` keeps the source directory out of the runtime binaries.
The bytecode caches (`__pycache__`) name their sources relative to the
prefix: `co_filename` of the code object in `config.cpython-314.pyc` is
`opt/sprite/python/curry/config.py`, and in the environment of 2026-10-07
none of the 13 caches of the library and none of the 181 of the package
holds an absolute path.  So they carry no path of the build machine; Python
does not use that path to find or to validate a module, and conda does not
rewrite them.  Since conda rewrites no `.py` file of the package, the caches
stay valid after the install: a cache is valid while the size and the
modification time of its `.py` file are the ones it recorded, and conda
keeps both (the environment of 2026-10-07 holds the 13 caches of the library
and the 181 of the package valid, `bytecode_is_current` of
`curry.backends.py.toolchain` on every file, and the `.py` files keep the
modification times of the build).  Before step 9 the text replacement
changed the generated `.py` files, and the first import of a library module
on the Python backend wrote its cache again.

The ABI stamp of a compiled module (`.so.abi`) was the one consequence of
the relocation that remained until issue #100 (2026-10-07).  It digested
the real path of the installation prefix (`toolchain.object_digest`), so
the shipped library objects counted as stale in every environment, whose
prefix is not the build prefix.  In the environment of the third build of
2026-10-07: the first import of the Prelude took 1.69 s, interpreted, with
a background compile that a short process cancels at exit (three short runs
wrote nothing); `sprite-make --so` of a program that imports Data.List took
30.9 s and wrote the objects and stamps of Prelude, Data.List and Data.Maybe
into `opt/sprite`, six conda-tracked files that then differed from the
record of `conda-meta` (`sha256_in_prefix`); a cancelled compile could leave
a shipped object without its stamp (Control.SetFunctions after example 10
under `sprite-exec`); and in a read-only installation the recompile failed,
so `sprite-make --so` of every program exited 1 (the compile step names the
cause since the review of that day; `tests/unit_conda.py` checks the
message) while `sprite-exec` ran with the library interpreted (1.8 s against
0.17 s from an object).  Since the change the stamp digests what decides
compatibility (the runtime headers, the flags of the flavor and of the
collector, the link flags, the compiler of the build as `make stage`
records it in `sysconfig/cxx_compiler`, and the format of the generated
code) and carries the real path of the installation as
text on its second line; `Cpp2So.is_stale` compares the digest with the one
of the runtime, and the text, as a real path, with the installation of the
process.  A copy made by hand names the original and stays stale; a package
whose stamps conda rewrote keeps its objects.  A probe of the same day in a
fresh environment with the 13 stamps rewritten, which is what the change
gives: the first import of the Prelude 0.20 s from the shipped object,
`sprite-exec` of the program 0.69 s then 0.18 s, `sprite-make --so` 3.4 s
(the precompiled header and the program), nothing written under
`opt/sprite`.  Since format 13 (2026-10-08) the objects name no path, so
the stamps are the one kind of file conda rewrites, and a test of the
repository relocates a copy of a staged installation and loads its library
from the copy with nothing compiled
(`test_relocated_installation_loads_its_objects` of `tests/unit_conda.py`).
No package build with either change has been made yet; open question 2
names what it must show.

The order of the chain is no longer at stake: the toolchain starts a
module from the newest file of its chain by modification time (issue #66),
conda rewrites the `.so` alone now, and the `.so` of a module is the last
file of its chain that the build wrote.

Dependencies:

| Kind  | Package                 | Why                                                     |
|-------|-------------------------|---------------------------------------------------------|
| build | `{{ compiler('c') }}`, `{{ compiler('cxx') }}`, `{{ stdlib('c') }}`, `make` | the C++ runtime and the extension |
| host  | `python 3.14.*`         | the extension module and the Python package             |
| host  | `curry-frontend 2.0.0.*` | `configure` checks it; `make install` runs it over the library |
| run   | `python 3.14.*`         | `python_abi` pins the CPython 3.14 ABI                  |
| run   | `curry-frontend 2.0.0.*` | Curry to FlatCurry; it brings `gmp` (libgmp)           |
| run   | `cxx-compiler`          | the C++ backend compiles generated code at run time     |

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
brings `gxx`, which has no activation script.  The wrapper adds no flag:
the installed headers need no header of the environment, so the
environment need not be activated.  `cxx-compiler` 2.0.0 brings GCC
15 with the conda-forge sysroot, so `conda_build_config.yaml` pins the
compiler of the build to GCC 15 as well:
the generated code is compiled against the headers under
`opt/sprite/include` and linked against `opt/sprite/lib/libcyrt.so`, and one
major version keeps one libstdc++ on both sides.  Move the pin together with
`cxx-compiler`.  The ABI stamps of the compiled library modules
(`.so.abi`) digest the runtime headers, the flavor flags and the compiler
of the build, as `make stage` records it in `sysconfig/cxx_compiler` (the
version and the target of `g++`), and carry the real path of the
installation as text, which conda rewrites at install time (see
"Relocation").  The record ships in the package, so an environment without
`cxx-compiler` computes the digest of the shipped objects all the same; a
package built with another compiler gives another digest, and its objects
are its own.  The
precompiled header of the runtime goes to the cache directory of the user,
`$XDG_CACHE_HOME/sprite/pch/<key>` or `~/.cache/sprite/pch/<key>`, where
the key is a digest of the real path of the installation: the C++ backend
puts it there when the installed include directory cannot be written or
lies in a conda environment (`config.cxx_pch_root`; `SPRITE_CXX_PCH_ROOT`
overrides the rule).  So the header is not written into the package at run
time.  The
cache grows: each installation leaves its own directory with a member of
about 70 MB, and nothing removes the directory of an environment that was
deleted (`remove_stale_members` works inside one key directory).  The
directory `pch` may be deleted at any time; the next compile builds the
member again.  The test step of conda-build is an installation too: the
two builds of 2026-10-07 left 151 MB in two keys under the `~/.cache` of
the builder before `build-packages.sh` pointed `XDG_CACHE_HOME` under the
build root (`BUILD_ROOT/cache`).

Tests (`meta.yaml`): the launchers, `import curry`, and one program on each
backend through `sprite-exec` and through `python -m curry`.  The library
comes compiled.  The C++ backend is the default: under its tiered mode a
short program runs interpreted and its background compile is cancelled at
exit, so the two default-backend tests check the value alone.  A third test
compiles the program with `sprite-make --so` and checks that the shared
object and the ABI stamp exist beside it (`.curry/sprite-pakcs-3.4.1/
Smoke.so` and `Smoke.so.abi`), which shows that the compiler of the
environment works; it also checks that the precompiled header went to the
cache directory of the user and not into the tree.  Two tests check the
relocation: no `.py` or `.cpp` file under `opt/sprite/curry` holds the
prefix, and the Prelude module object names its source under the prefix
and has its type signatures (`curry.typeof`, which reads the FlatCurry
interface beside the source).  The two Python-backend tests select the
backend with `SPRITE_INTERPRETER_FLAGS=backend:py`.  The test step of the
build of 2026-10-07 took 1 min 1 s.

Package contents (the build of record of 2026-10-07, the third of the
day): 713 files, 2.8 MB compressed (2,791,180 bytes; the second build
2,747,127 bytes, the first, with Boost, 2,747,197 bytes), 26 MB on disk.

| Directory                        | Files | Size   | Contents                                                   |
|----------------------------------|------:|-------:|------------------------------------------------------------|
| `bin/`                           |     2 |        | the launchers `sprite-exec` and `sprite-make`              |
| `lib/python3.14/site-packages/`  |     1 |        | `sprite.pth`                                               |
| `opt/sprite/python/`             |   363 | 4.7 MB | the package `curry`: 181 modules, their bytecode, the extension module |
| `opt/sprite/curry/`              |   282 |  21 MB | 22 sources with LICENSE and NOTICE; FlatCurry, interfaces, ICurry and JSON of every module; Python, bytecode, C++, shared object, and ABI stamp of the 13 compiled modules |
| `opt/sprite/include/`            |    40 | 264 KB | the runtime headers                                        |
| `opt/sprite/lib/`                |     1 | 708 KB | `libcyrt.so`                                               |
| `opt/sprite/sysconfig/`          |    16 |        | the settings Sprite reads at run time                      |
| `opt/sprite/bin/`, `opt/sprite/tools/` | 8 |     | the scripts of the tree; the links `python` and `curry-frontend`, the wrapper `cxx` |

The dependencies of the package are `__glibc >=2.17,<3.0.a0`,
`curry-frontend 2.0.0.*`, `cxx-compiler`, `libgcc >=15`, `libstdcxx >=15`,
`python >=3.14,<3.15.0a0`, and `python_abi 3.14.* *_cp314` (the first build
of 2026-10-07 had `libboost-headers` as well; the dependency cleanup of the
same day dropped Boost from the runtime, and the build of record has no
Boost package and no Boost include in its headers).  The environment of
2026-10-07 resolved them to python 3.14.8, gxx 15.3.0 (through cxx-compiler
2.0.0), libstdcxx 16.2.0, sysroot_linux-64 2.39, gmp 6.3.0 and
curry-frontend 2.0.0 pakcs341_0.
An environment with the package and its dependencies takes about 1.4 GB,
most of it the compiler, its sysroot, and Python.

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

The script `build-packages.sh` runs the build.  Its source is an export of
a commit, `git archive` of HEAD by default, with the pybind11 submodule
exported at the commit the superproject records; so an untracked or a
modified file of the working tree never ships, and the links `install`
and `object-root` of a developer tree stay out.  The recipe keeps
`path: ../..`, which inside the export is the exported tree.  conda-build
needs nothing for this beyond the export: `git` on the machine, and a
checkout of the submodule that holds the recorded commit.  (The other
form, `git_url: ../..` in `meta.yaml`, makes conda-build clone HEAD
itself; it then runs `git submodule update --init --recursive`, which
fetches pybind11 from GitHub on every build, so the build needs the
network for the source as well, and a tree without `.git` cannot be
built.  The export was preferred.)

    conda create -p /path/to/build-env --override-channels -c conda-forge conda-build
    export CONDA_PKGS_DIRS=/path/to/pkgs     # optional: a writable cache
    conda/build-packages.sh --build-root /path/to/build-root \
        --conda /path/to/build-env/bin/conda \
        --pakcs-archive /path/to/pakcs-3.4.1-amd64-Linux.tar.gz \
        --jobs 4 --memory-limit 16

The script exports the commit to `BUILD_ROOT/src/sprite-<commit>`, builds
`curry-frontend` and then `sprite` from the recipes of the export, with
`--croot BUILD_ROOT/bld` and the output folder `BUILD_ROOT/channel`
(`--channel` names another), the local channel first and conda-forge
second.  `--pakcs-archive` copies a PAKCS archive that is already on disk
into `BUILD_ROOT/src_cache` under the name conda-build uses, the file name
with the first ten characters of its SHA-256 (the script checks the hash
against `curry-frontend/meta.yaml`), so the build downloads nothing but
conda packages.  `--jobs` sets `CPU_COUNT`, `--timeout` the time limit of
each build (3600 s by default), and `--memory-limit GB` runs each build
under `prlimit --as`.  `--skip-frontend` builds `sprite` alone, from the
`curry-frontend` the channel holds; `--export-only` stops after the
export; `--dry-run` prints the plan.  `--overlay PATH` takes a file or a
directory of the working tree in place of the exported one, for a build of
uncommitted work; the path is normalized (`realpath -m`), and a path that
leaves the repository or names it (`..`, `conda/..`, `.`) is refused,
because it would replace the export with the working tree; a package built
with overlays is a development build, and the record of such a build must
say so.

conda-build runs in a scrubbed environment (`env -i` with `PATH`, `HOME`,
the locale, `TMPDIR`, `CPU_COUNT`, `XDG_CACHE_HOME` set to
`BUILD_ROOT/cache`, the proxy variables, `CONDA_PKGS_DIRS`, `USER` and
`LOGNAME`).  A conda environment that is active in the shell,
or the variables of a conda compiler (`CC`, `CXX`, `CFLAGS`, `CXXFLAGS`,
`LDFLAGS`), would otherwise reach the build: the test step activates the
test environment, which first deactivates the active one and runs its
deactivation scripts, and the activation scripts of a conda compiler add
their flags and include directories.  The plan names the passed variables
but not their values, because a proxy variable can hold a credential.
`/tmp` must be writable: the activation scripts of the conda-forge
compilers write `/tmp/old-env-<pid>.txt` during a build (a sandbox that
mounts `/tmp` read-only fails there with "Read-only file system").

By hand, the same build is

    cd /path/to/Sprite
    conda build conda/curry-frontend --croot $croot --output-folder $channel \
        --override-channels -c conda-forge
    conda build conda/recipe --croot $croot --output-folder $channel \
        --override-channels -c file://$channel -c conda-forge

from the working tree, with whatever it holds.

The `curry-frontend` build takes about two minutes (2 min 19 s on
2026-10-07).  The `sprite` build of record of 2026-10-07 (the second build
of that day, without Boost) took 4 min 57 s from the creation of its
environments to the end of its tests (the test step 48 s; the script with
the export, 5 min 11 s) with `CPU_COUNT=4` and a warm package cache; the
first build of the day, with `libboost-headers`, took 7 min 23 s.  Most of
that time is the C++ runtime and the 13 library modules.


Testing the packages
--------------------

An environment with both packages, from the local channel:

    conda create -p /path/to/env --override-channels -c file://$channel -c conda-forge sprite python=3.14

Then, from a directory outside the repository and without activation of
the environment, with a program `Smoke.curry`:

    /path/to/env/bin/sprite-exec Smoke.curry
    SPRITE_INTERPRETER_FLAGS=backend:py /path/to/env/bin/sprite-exec Smoke.curry
    /path/to/env/bin/python -m curry Smoke.curry
    /path/to/env/bin/python -c 'import curry; from curry.lib import Prelude; print(next(curry.eval(curry.expr(Prelude.length, [1, 2, 3]))))'

The environment test of 2026-10-07 (the environment made from the
packages of this text, each command in a scrubbed environment, `env -i`,
no `SPRITE_HOME`, no `CXX`):

| Command                                   | Backend | First run | Second run |
|-------------------------------------------|---------|----------:|-----------:|
| `python -c 'import curry'`                |         |    0.11 s |            |
| `python -c` import of the Prelude, one call | cxx   |    1.86 s |     1.63 s (0.13 s after `sprite-make --so` had compiled the Prelude) |
| `sprite-make --icy Warm.curry` (imports every library module) | | 0.77 s |    |
| `sprite-exec Smoke.curry`                 | cxx     |    2.43 s |     2.02 s |
| `sprite-exec Smoke.curry`                 | py      |    0.91 s |     0.20 s |
| `python -m curry Smoke.curry`             | cxx     |    2.40 s |            |
| `python -m curry Smoke.curry`             | py      |    0.18 s |            |
| `SPRITE_INTERPRETER_FLAGS=interpret:all sprite-exec Smoke.curry` | cxx | 2.37 s | |
| `sprite-make --so Smoke.curry`, then `sprite-exec` | cxx | 30.9 s | 0.2 s   |
| `examples/10-queens-set-functions/run`    | cxx     |    0.75 s |            |
| `examples/24-build-system/run`            | cxx     |   11.9 s  |            |

`Smoke.curry` imports Data.List and has two values.  The numbers are those
of the environment of the build of record; the environment of the first
build of the day gave the same picture within 0.3 s.  The two examples ran
their run scripts from copies outside the repository with
`SPRITE_HOME=<env>/opt/sprite` (the scripts default to the install of a
checkout), and both outputs matched `expected.out`; `go.py` and `make.py`
also ran through the Python of the environment with no `SPRITE_HOME` set.
`sprite-make --so` compiled the stale Prelude, Data.List and Data.Maybe
first (open question 2), and the precompiled header of the runtime, which
went to `$XDG_CACHE_HOME/sprite/pch/<key>` (71 MB).  The shared object of
the program names the dynamic loader `/lib64/ld-linux-x86-64.so.2`, as the
Python of the environment does.  After the runs, the files written under
the environment were the objects and stamps named under "Relocation", and
`lib/python3.14/__pycache__/_sysconfigdata__linux_x86_64-linux-gnu.cpython-314.pyc`,
which Python writes for its own `sysconfig` module.  The 13 bytecode caches
of the library and the 181 of the package were valid.  The runs were made
with `XDG_CACHE_HOME` set to a scratch directory; without it the header
goes to `~/.cache/sprite`, where the test step of conda-build put it until
`build-packages.sh` pointed `XDG_CACHE_HOME` under the build root.

The environment of the third build (the build of record) repeated the
measurements that the review had questioned, each command again under
`env -i` with the `bin` of the environment on `PATH`: `import curry`
0.10 s; the first import of the Prelude 1.69 s, interpreted; `sprite-exec`
2.32 s on cxx and 0.64 s on py, and those three short runs wrote nothing
under the environment.  With the directories of `opt/sprite` made
read-only, `sprite-make --so` exited 1 in 0.7 s with the message of the
compile step, `sprite-exec` ran the program twice in 1.8 s each, and no
file of the package changed.  Writable again, `sprite-make --so` took
30.9 s and wrote the six files of Prelude, Data.List and Data.Maybe (the
six files that then differ from the record of `conda-meta`); `sprite-exec`
then took 0.17 s and the import of the Prelude 0.14 s, from the new
objects.  The 13 caches of the library and the 181 of the package were
valid, and none of the 194 holds an absolute source path.  The precompiled
header (71 MB) went to `$XDG_CACHE_HOME/sprite/pch/<key>`, and nothing new
appeared under `~/.cache/sprite`.  The tree under `opt/sprite` takes 26 MB
on disk.

The unit tests of the recipe files, `tests/unit_conda.py`, run with the
test drivers of the repository.  They check the recipe files, the build
script (its dry run and its export), the launcher, the rule of the
precompiled header, the dynamic loader path, the relocatable generated
files, and the build options the recipe relies on, not a build.

Status
------

Both recipes were built on 2026-10-07 with conda-build 26.9.1 (conda
26.9.1, Python 3.13) on linux-64 with `build-packages.sh`, from the export
of commit f9ce8077 with the uncommitted files of the working tree as
overlays (a development build: the packaging work of this directory and
the dependency cleanup that dropped Boost, both uncommitted at the time),
and from the PAKCS archive of the source cache.  `sprite` was built three
times that day: first with `libboost-headers` (the overlays of the
packaging work alone), then without it (every changed path of the working
tree), and a third time after the review of the two lanes (every changed
path again, with the corrections of the review: the compile step that
names a read-only directory, the overlay check and the cache directory of
`build-packages.sh`, the recipe comment).  The third build is the build of
record: 2,791,180 bytes, 713 files, 12 binary entries in `info/has_prefix`
and no text entry, 3 min 44 s of conda-build with the test step (CPU time
1 min 41 s for the build, 27 s for the tests), the script 3 min 59 s with
`--skip-frontend`.  Against the second build, 222 of its files differ in
content (the 13 objects and their stamps, which digest the build prefix;
the 194 bytecode caches, which record the modification times of their
sources; `toolchain.py` and its cache, the one change of size, 1,929
bytes), and the compressed archive is 44,053 bytes larger.  All three
builds passed their tests.
An environment made from each `sprite` build and `curry-frontend` ran the
test of the section above on both backends without activation, with no
`SPRITE_HOME` set.  The ICurry oracle of `tests/README` was not run against
these builds.  The build of 2026-10-05 (conda-build 26.9.1, the working
tree of the branch) was the first.

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
   its first compile, into the cache directory of the user.
6. Nothing is written into the package at run time (2026-10-07; the
   library objects since the stamp change of issue #100, which the next
   build verifies).  The precompiled header goes to
   `$XDG_CACHE_HOME/sprite/pch/<key>` or `~/.cache/sprite/pch/<key>` when
   the include directory of the installation cannot be written or lies in
   a conda environment; the generated files of the library name their
   sources relative to the installation, so conda rewrites no text file
   and the shipped bytecode stays valid.  Before the stamp change,
   `sprite-make --so`, or a process that outlived the background compile,
   compiled the stale library objects again into `opt/sprite` (six
   conda-tracked files in the environment test of 2026-10-07), and in a
   read-only installation that compile failed (see "Relocation").
7. The source of the package is an export of a commit, through
   `build-packages.sh`.  The recipe keeps `path: ../..`.
8. The version of the package is the `VERSION` file, read at render time.
9. No Boost: the runtime uses the C++17 standard library alone since the
   dependency cleanup of 2026-10-07, so `libboost-headers` is out of the
   host and run requirements, and the compiler wrapper adds no include
   flag.

Open questions
--------------

Resolve these before anything is published.  The license question of the
first scaffold is closed: `LICENSE` at the root of the repository is the
BSD 3-Clause license of Sprite, and the package ships it with the notices
of the Curry library (`curry/lib/LICENSE`, `curry/lib/NOTICE`) and of
pybind11.  Questions 3, 10, 11, 13 and 14 were decided on 2026-10-07, the
stamp of question 2 under issue #100 the same day, and the objects of
question 2 on 2026-10-08 (format 13 of the generated code); the entries
record the decisions.

1. The front end.  Keep the separate package.  The binary has its own
   license and origin, it moves with PAKCS and not with Sprite, and a
   package that downloads at run time is not acceptable on conda-forge.  To
   publish it, a feedstock `curry-frontend` is the first step; a second
   platform needs a build of the front end from source (GHC, Stack resolver
   lts-16.9).  Open.
2. The compiler at run time, and the ABI stamp.  Keep `cxx-compiler` as a
   run dependency for now: the first user must get compiled code from one
   command.  Later, split the package: `sprite` with the C++ runtime, its
   ICurry interpreter (the interpreter flag `interpret`) and the compiled
   library objects, which runs without a compiler, and a metapackage
   `sprite-cxx` that adds `cxx-compiler` for the background compile of the
   user's modules.  The split is a follow-up of the packaging issue #1;
   stage 2 of issue #82 (the compiler-free mode) documented the behaviour
   and did not split the package.  The stamp: decided on 2026-10-07 under
   issue #100 and applied there.  The ABI stamp digests what decides
   compatibility (the runtime headers, the flags of the flavor and of the
   collector, the link flags, the compiler of the build and the format of
   the generated code) and carries the real path of the
   installation as text on its second line (`Cpp2So` of
   `curry.backends.cxx.toolchain` documents the format); `is_stale`
   compares the digest and the text.  So the shipped library objects stay
   in use once conda rewrote the stamps, a copy made by hand stays stale,
   and the recompile into the package and its failure in a read-only
   installation (see "Relocation") are gone.  What the recipe needs:
   nothing in `meta.yaml`.  conda-build finds the prefix in a text file by
   itself and lists the file in `info/has_prefix` as a text entry (the
   setting `detect_binary_files_with_prefix` concerns the binary files
   alone), and conda rewrites a text entry at install time.  `build.sh`
   turns the product cache of the C++ backend off
   (`SPRITE_PRODUCT_CACHE=`), so the build compiles its own library
   objects and the package holds files, not hard links into a cache.  The
   objects: since format 13 of the generated code (2026-10-08) a compiled
   module names the modules it imports by `SONAME`, not by path, and its
   record names a source outside the installation relative to the object,
   so no binary file of the package holds the prefix and `info/has_prefix`
   holds the stamps as text entries alone; the relocation of the objects
   is tested in the repository (`test_relocated_installation_loads_its_objects`
   of `tests/unit_conda.py`: a copy of a staged installation with its
   stamps rewritten loads the library from its own objects, compiles
   nothing, and maps no object of the original).  What the next build must
   show: 13 text entries and no binary entry in `info/has_prefix` (the
   stamps; a binary entry means an object holds the prefix again); in an
   environment, a stamp whose second line is the prefix of the environment
   (`<env>/opt/sprite`), `readelf -d` of `Data/List.so` with
   `sprite-Prelude.so.13` and no path among its `NEEDED` entries, the first
   import of the Prelude from the shipped object, `sprite-make --so` of a
   program without a recompile of the library, and no file of the package
   changed after the runs.  The stamp holds the real path, so the build
   prefix must be a real path for conda-build to find it (a build root
   without a link in it).  A system compiler should stay out: the generated
   code must see the libstdc++ headers of a compiler that matches the
   runtime library of the environment.  The stamp and the objects are
   closed; open: the split.

3. Writes into the package at run time.  Decided on 2026-10-07; see
   decision 6.  The precompiled header: `config.cxx_pch_root` chooses the
   cache directory of the user when the installed include directory cannot
   be written or lies in a conda environment (a `conda-meta` directory
   above it); the key of the per-installation directory is a digest of the
   real path of the installation, because the toolchain removes the stale
   members of the directory it uses and two installations would otherwise
   remove each other's members; `SPRITE_CXX_PCH_ROOT` keeps its meaning as
   the override, and the empty value disables the header.  The bytecode
   caches: the generated Python names its source relative to the
   installation (step 9 of the build), so conda rewrites no `.py` file and
   the shipped caches stay valid.  The shared object of a library module
   compiled again by `sprite-make --so`, or by a process that outlives the
   background compile of its first import: the cause is the ABI stamp,
   open question 2; the order of the chain is no longer at stake (issue
   #66).  The cache directory of the header is not garbage-collected (see
   "The compiler").
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
   One source of truth for the two would be better.  The proposal of the
   dependency cleanup of 2026-10-07, not applied: read the pins of
   `configure` (`PINNED_FRONTEND_VERSION`, `PINNED_PAKCS_VERSION`) at
   render time with `load_file_regex`, as the version reads `VERSION`, in
   both recipes; the copies in `scripts/setup-dev-machine.sh`, the CI
   workflow and two tests would stay.  Open.
6. The compiler pin.  `conda_build_config.yaml` pins GCC 15 for the build.
   On conda-forge the global pinning sets the compiler version and the
   feedstock drops this file; the run dependency `cxx-compiler` then gives
   whatever major version conda-forge ships, and the generated code may be
   compiled by a newer compiler than the runtime.  That is the normal
   libstdc++ case (a newer compiler with a runtime library at least as new
   as the build's, which the run export keeps).  Probe of 2026-10-07:
   conda-forge offers `gxx_linux-64` 16.2.0, but `cxx-compiler` 2.0.0
   depends on `gxx 15.*`, so an environment with the package and GCC 16 does
   not solve; the probe used a second environment with `gxx_linux-64=16` and
   named its compiler through `SPRITE_CXX`.  `sprite-make --so` compiled the
   program in 4.5 s against the headers of the package, the object needs
   `GLIBCXX_3.4.32` at most, and `sprite-exec` ran it from the object with
   the `libstdcxx` 16.2.0 of the environment.  One limit of the wrapper
   showed: the member name of the precompiled header digests the real path
   of `tools/cxx`, not of the compiler behind it, so two compilers used
   through `SPRITE_CXX` share one member, and g++ ignores a member of
   another compiler (a slower compile, not an error).  Two other options tie
   the two sides.  A run dependency or a `run_constrained` entry `gxx {{
   cxx_compiler_version }}.*` makes the compiler of the environment the
   compiler of the build; today `cxx-compiler` 2.0.0 itself depends on `gxx
   15.*`, and a later `cxx-compiler` moves on without this recipe noticing.
   Or drop the local pin and take the compiler of the pinning file on both
   sides.  Decide before publication.

7. macOS.  Sprite's Makefiles use GNU make, `realpath`, `flock`, and GNU
   linker flags (`--whole-archive`, `--no-undefined`, `-z undefs`).  The front
   end binary comes from the Linux distribution of PAKCS only; macOS needs
   the PAKCS or KiCS2 distribution for macOS, or a build of the front end
   from source with GHC (Stack resolver lts-16.9).  The run path of the
   extension module uses `$ORIGIN`, which is `@loader_path` on macOS.  Open.
8. Windows.  Not planned: the build system is make and bash, the C++
   backend assumes ELF shared objects and `dlopen`, and the front end has no
   Windows binary.  Open.
9. PAKCS.  The package has no PAKCS, so `tests/oracle` cannot run the
   functional tests against it.  The unit tests run without PAKCS.  Open.
10. Versions.  Decided on 2026-10-07: `recipe/meta.yaml` reads the
    `VERSION` file at render time
    (`load_file_regex(load_file="../../VERSION", ...)`); `conda render`
    shows `version: '0.9'`.  `tests/unit_conda.py` checks that the recipe
    hard-codes no version.
11. The source of the Sprite recipe.  Decided on 2026-10-07: an export of
    a commit through `build-packages.sh` (see "Building locally"); a build
    straight from the working tree stays possible and ships whatever the
    tree holds.  A published recipe should list two `url` sources, the
    release tarball and the pybind11 tarball with `folder:
    extern/pybind11`, or add the conda-forge package `pybind11` to the host
    requirements, whose headers the compiler finds under `$PREFIX/include`;
    a release tarball from GitHub lacks the submodule.
12. Pip.  A wheel of the Python backend (roadmap issue #1) needs the front
    end on the user's machine; the conda package solves that through
    `curry-frontend`.  A wheel that bundles the front end binary would carry
    a 9 MB binary per wheel and the PAKCS license.  Decide the channel of
    the conda packages first.  Open.
13. `ld_interpreter_path`.  Documented on 2026-10-07 as a fact with a test.
    The sysconfig value is a fixed file of the repository
    (`src/export/sysconfig/ld_interpreter_path.var`): the dynamic loader of
    glibc on x86-64 Linux, `/lib64/ld-linux-x86-64.so.2`.  The C++ backend
    writes it into the `.interp` section of the shared object of a module
    with a `main` goal (`curry.backends.cxx.compiler._generate_main`).  It
    is the one sysconfig value that names a path of the machine, and the
    one assumption the package makes about the machine outside the
    environment.  `tests/unit_conda.py` (`test_ld_interpreter_path`) checks
    that the value is the `PT_INTERP` of the Python of the installation and
    a file that exists; in the environment of 2026-10-07 the Python of the environment names `/lib64/ld-linux-x86-64.so.2`, the compiled program `Smoke.so` carries the same path in its `.interp` section (`readelf -l`), and the file exists on the machine.  A
    second platform, or a libc other than glibc, needs another value: let
    `configure` read the `PT_INTERP` of the Python of the environment, or
    drop the section if nothing runs the shared objects directly.
14. The sysroot at run time.  Documented on 2026-10-07 as a fact.  The
    build compiles against the conda-forge sysroot 2.17
    (`c_stdlib_version`).  The C++ backend compiles generated code against
    the sysroot of the environment, which the recipe does not pin: the
    environment of 2026-10-07 got `sysroot_linux-64 2.39` with `gxx 15.3.0` and `libstdcxx 16.2.0` (the package
    `sysroot_linux-64 2.39` depends on `__glibc >=2.39`, so a machine with
    an older glibc gets an older sysroot).  The generated code thus sees
    the glibc headers of a newer sysroot than the runtime library was built
    with.  That worked here, as the compile test of the package and the
    environment test show, and it is the normal case for glibc, but it is
    untested on another machine.  A run dependency `sysroot_linux-64
    2.17.*` would give the generated code the headers of the build
    everywhere.  Decide before publication.
15. The notices of the front end.  `pakcs-frontend` is a GHC executable:
    its Haskell libraries are linked into it statically, and the strings of
    the binary name GHC 8.8.3 and the packages binary, bytestring,
    containers, extra, network-uri, parsec, pretty, process, set-extra,
    time, transformers, and unix, besides curry-frontend itself.  The
    package `curry-frontend` ships the PAKCS license and the front-end
    license only, not the notices of those libraries.  (libgmp is linked
    dynamically and comes from the conda package `gmp` with its own
    notices.)  Open.

What remains before publication
-------------------------------

Publication and the channel are the owner's decisions.  Before them:

1. The front end (question 1): a feedstock `curry-frontend`, and a build
   of the front end from source for a second platform.
2. The ABI stamp and the objects (question 2): applied under issue #100
   and the format-13 change of 2026-10-08; the next build verifies that
   `info/has_prefix` holds the 13 stamps as text entries and no binary
   entry, and the runs named under question 2.  Then decide the split into
   `sprite` and `sprite-cxx`.
3. The compiler pin (question 6): take the compiler of the pinning file on
   both sides, or tie them with `run_constrained`; the probe with GCC 16
   is recorded in the entry.
4. macOS and Windows (questions 7 and 8): out of scope for linux-64; say
   so on the channel.
5. The oracle (question 9): the functional tests cannot run against the
   package; the unit tests can.
6. Pip (question 12): after the channel.
7. The notices of the front end (question 15): list the Haskell libraries
   of the pinned front end from its cabal file and add their license files
   to `license_file`.
8. The sysroot (question 14): decide whether to pin `sysroot_linux-64` at
   run time.
9. A build without overlays, from a commit that holds the packaging work,
   before the first upload: the builds of 2026-10-07 are development
   builds.
10. The metadata of the artifact (the review of 2026-10-07): the recipes
    name no path of the build machine, but the package does.
    `info/recipe/meta.yaml` of a build holds the path of the export
    (`path: BUILD_ROOT/src/sprite-<commit>`) and a comment with the same
    directory, `info/about.json` the URL of the local channel
    (`file://BUILD_ROOT/channel`), and `info/has_prefix` the build prefix
    under `BUILD_ROOT/bld`, as every conda package records its
    placeholder.  Before an upload, build the release package from a
    neutral path, or through a CI feedstock, and inspect `info/recipe` and
    `info/about.json` (`conda build --no-include-recipe` leaves the recipe
    out of the package).
11. A read-only installation (question 2): resolved by the stamp change of
    issue #100 once the next build verifies it.  Until then the C++
    backend cannot compile a program in an environment whose `opt/sprite`
    cannot be written, because the stale library objects must be compiled
    again first (`sprite-make --so` fails and names the cause;
    `sprite-exec` runs the program with the library interpreted).
12. One source of truth for the front-end pin (question 5).
