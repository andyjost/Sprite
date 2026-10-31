# Sprite

Sprite is a compiler and runtime for the Curry functional logic language,
based on the Fair Scheme. It has a C++ runtime behind a Python API. The
design is described in the author's dissertation:
https://doi.org/10.15760/etd.3564

## Status (2026)

The default tool pair is front end 3.1.0 with PAKCS 3.10.0; CI keeps
front end 2.0.0 with PAKCS 3.4.1 in advisory `legacy-tools` shards.
The distribution `curry` 0.9.0a3 is the current release (the tag of
2026-10-31), with wheels for Linux x86-64 and aarch64, macOS 15 or newer
and Windows x64 on Python 3.11 to 3.15, and `curry-frontend` 3.1.0.post2
for the same platforms, on PyPI since 2026-10-31.

The work happens on `master`. The refresh for current tools (Python
3.14, PAKCS 3.4.1) was done on the branch `py314`, which `master` took
over on 2026-10-17; the branch was deleted on 2026-10-30, its history is
in `master`.
The Python API is the surface of the API review of October 2026:
`curry/__init__.pyi` is the installed stub and `tests/unit_surface.py`
checks the package against it. The files `tests/unit_flow_f*.py` and
`tests/unit_stub_*.py` are its frozen acceptance tests; 432 of 435 pass on
the C++ backend. The three `expectedFailure` markers there are F13's
`test_choice_protocol` and `test_fork_precedence`, and
`unit_stub_terms.py::test_choice_type_conversion`, awaiting the choice
interpreter. Two assertions of `unit_stub_terms.py` were corrected on
2026-10-25: `True & False` has no value (#139), as in PAKCS and KiCS2.
D45 fixes #171: a capsule with no value and an outside failure fails even
when it also recorded inside failures.
The failure half of the whole-cell read of N is implemented (D53), following
transparent forward chains before descent; CursorFail tests exhaustion with
no value, while the constraint half (CursorBeta: exactly Pair True True and
termination) awaits decision D59, pending with the owner.
The Python backend was removed on 2026-10-24 at the owner's
word (B4, issue #82).
F11's `test_free_argument_answers` passes:
partial lists in values and bindings print cons without spaces, as PAKCS
does. The tracker reproducers are `tests/unit_issue{103,104,108,133,134,137}.py`;
#133 and #134 were fixed on 2026-10-25 (a lifted constraint keeps its set
guards; a one-constructor generator forks to its one instance); their
reproducers pass.

## Layout

- `src/python/`: the `curry` Python package (interpreter, compiler, backends).
  `src/python/typecheck/` is the typed boundary: the signature table reads
  the type schemes from the FlatCurry interfaces (`symbol.signature`),
  `defaulting.py` applies the table of the PAKCS REPL to the class
  constraints of a goal, `goals.py` builds the goal with its dictionaries
  for `curry.eval`, `curry.parse`, the REPL, `sprite-exec
  -g` and saved modules, and the engine types a Python-built expression
  (`engine`, `terms`, `unify`, `instances`, `exprtype`, `errors`), with
  `builder.py` as the typed construction behind `curry.term` and the
  calls of a symbol over it, and `serialize.py` as the printer of a
  description as Curry text.
  `src/python/tools/icy/` is the REPL: `python -m curry.tools.icy`, with
  `:load`, `:reload`, `:eval`, `:type`, `:set` and `:quit`.
- `src/curryrt/`: the C++ runtime library.
- `curry/`: the Curry library. `curry/lib/` holds a copy of the library of
  the pinned PAKCS, Sprite's own `Control.SetFunctions`, the license of the
  origin, and the pinned ICurry products. See `curry/README.md`.
- `tests/`: unit tests (`unit_*.py`) and functional tests (`func_*.py`).
  `tests/README` explains the layout, the drivers, and the oracle.
- `docs/`: Sphinx sources.
- `assets/`: the logo (`assets/logo/`): a burst of dust as the mark and
  the icon, the wordmark with a twig wand in place of the i, the lockup of
  the two, the palette, the generator and a specimen sheet;
  `assets/logo/README.md` describes them and the rules of use. The sdist
  leaves the directory out.
- `contrib/`: editor support outside the package: the Vim syntax of the
  trace log (`contrib/vim/`, with its `ftdetect` file).
- `examples/`: runnable examples.
- `conda/`: the scaffold of a conda package for linux-64, not published.
  `conda/README.md` describes the two recipes and the open questions.

## Requirements and policy

- Python 3.11 to 3.15 (3.11.4 minimum). Do not add `six` or compatibility
  code for Pythons older than 3.11.
- The pinned front end is 3.1.0 with PAKCS 3.10.0 as the test oracle.
  The legacy pair, front end 2.0.0 with PAKCS 3.4.1, remains accepted
  through the same CMake options. PAKCS itself is optional at build time:
  `-DWITH_PAKCS=` with `-DWITH_CURRY_FRONTEND=PATH` builds without it.
  The selected pair names the intermediate directories and the PAKCS CPP
  macro (310 by default, 304 for the legacy pair). Every library module
  ships pinned `.icy`, `.fint`, `.icurry`,
  `.icy.imports` and `.icy.source` products for front end 3.1.0, so a build
  without a front end uses them after checking source receipts; the legacy
  pair compiles the library afresh at stage time. The reader accepts both
  FlatCurry grammars.
  One copy of base 3.4.0, from PAKCS 3.10.0, serves both front ends
  (`curry/README.md`). The typed boundary reads both grammars of instance
  and implementation names; nullary and multi-parameter classes await the
  next stage of the typed API.
- Curry is translated to ICurry in three steps: the front end
  (`bin/pakcs-frontend` of PAKCS) writes FlatCurry; the rewrite step
  (`flat2icurry.rewrite_file`) rewrites the `.fcy` file in place, when a
  pass changes the program, with two passes: the binding optimization of
  PAKCS (`flat2icurry.bindingopt`, which turns a Boolean equality that a
  condition requires to be True into `constrEq`, as PAKCS does before any
  compiler reads the file) and the set0 lift (`flat2icurry.setlift`,
  which turns `set0 e` over the captured variables `x1 .. xk` of `e` into
  `setk L x1 .. xk` with a new private function `L x1 .. xk = e`, so the
  captured variables are arguments of the capsule, boxed at the entry;
  decision D28 of 2026-10-12); and `curry.toolchain.flat2icurry`, a
  Python port of `icurry` 3.1.0/3.3.0, writes ICurry. The `icurry` program is an
  optional alternative for the last step, configured with CMake `-DWITH_ICURRY=PATH` and selected with `SPRITE_CURRY2ICURRY=icurry` or
  `sprite-make --curry2icurry icurry`; it reads the rewritten file too, so
  both routes translate the same input. The optional preprocessor `currypp`
  is found on PATH and shipped by neither Sprite nor the front-end package;
  tests skip modules that need it when absent, and benchmarks exclude them.
  In compatibility mode the port is
  byte-identical to icurry 3.1.0 with front end 2.0.0 and icurry 3.3.0 with
  front end 3.1.0, checked against the archives `overlay-pakcs-3.4.1.tgz`
  and `overlay-pakcs-3.10.0.tgz` under `tests/overlay/` (`tests/README`).
  CMake rejects
  mismatched version pairs. The archives are selected by the configured
  release; the current-tool archive includes all 30 library oracles.
  The runtime route uses `icurry_compat=False`: it looks through root type
  annotations and keeps the new front end's completed case order (see
  `src/python/toolchain/_frontend.py`). An `.icy` translated before a
  pass of the rewrite existed is stale (its `.fcy` holds an equality the
  binding optimization replaces and neither file holds `constrEq`, or
  holds a `set0` call the lift lifts and the `.icy` lacks the lifted
  function; the library is left out)
  and is made again at the first import, by `sprite-make` or by the
  prepare pass of the tests, which report the count;
  `sprite-make --rewrite-flat M` runs the step again for one module,
  current or not, and `python -m curry.toolchain.flat2icurry.rewrite
  M.fcy` rewrites the file alone. A run of the front end rewrites every
  `.fcy` it wrote, those of the imports it compiled again included. A
  hit of the ICurry cache of the test drivers rewrites the `.fcy` of the
  module as well, so the file matches the ICurry it serves; a file older
  than the source, missing, or in a read-only directory is left alone.
  The key of that cache names the version of the route
  (`ROUTE_VERSION` of `_frontend.py`). The front end's warning on
  overlapping rules is reported once per module through the log at the
  WARNING level; `SPRITE_FRONTEND_WARNINGS=0` silences it, and the test
  runner, the test library, the benchmark harness and the run scripts of
  the examples whose rules overlap by design set it.
- The construction of a term from Python is typed
  (`src/python/typecheck/builder.py`): `curry.term(value, type=...)`
  converts a Python value by its type or the stated one; a call of a
  symbol, `M.f(1)`, reads the scheme of the FlatCurry interface, unifies
  the arguments with the parameter types, defaults the class constraints
  with the table of the PAKCS REPL and supplies the dictionaries;
  `curry.parse(text, imports=...)` builds a term from Curry text. A
  typing failure is a `CurryTypeError` at construction. `curry.typeof`
  (`defaulted=True` applies the table) and `curry.show` complete the
  API; the installed stub `curry/__init__.pyi` is the surface.
- Other tools: a C++ compiler (g++ or clang++; clang-cl on Windows), GNU make, and binutils (`ar`). The
  C++ runtime uses the C++17 standard library and privately links the
  public domain libtommath 1.3.0, the submodule at extern/libtommath,
  shipped beside extern/mps and extern/pybind11 (no system libtommath is
  needed); Boost is not needed. The runtime, the bindings, the generated
  code and the C++ tests compile with `-fno-strict-aliasing`: the node
  graph is read through the pointer union `NodeU`, which the aliasing
  rules of C++ do not describe (issue #170, found on riscv64).
  jq is not needed: Sprite writes compact JSON itself. SWI-Prolog runs
  PAKCS, the test oracle, and the build of its saved states; Haskell Stack
  builds PAKCS from source; Sprite itself needs neither. GNU time
  (`/usr/bin/time`) is optional: the benchmark harness uses it for the peak
  memory of a run.
  The benchmark harness also has a separate community suite; its manifest
  and wrapper rules are in `tests/data/curry/benchmarks/README.md`.
  On Windows, clang-cl of Visual Studio builds the runtime and the
  bindings (the workflow `windows.yml`, on windows-2025, in the developer
  environment of vcvars64; cl is experimental); the services of the
  operating system are behind `curryrt/platform.hpp`, the data symbols
  that other objects read carry `CURRYRT_DATA` (`curryrt/export.hpp`),
  and the compile of generated code is not available there: the library
  ships its ICurry and JSON, every module runs interpreted (the flag
  `interpret` defaults to `all` on Windows), and there are no Windows
  wheels yet.
- Sprite needs no GPU.
- CMake honours `CC`, `CXX`, `CFLAGS`, `CXXFLAGS`
  and `LDFLAGS` from the environment, so build in a clean environment when
  a conda or cross toolchain is active.

## Build and test

- CMake 3.24 or newer, Ninja and the build Python come from PATH (conda or
  system). `make check-prereqs` diagnoses missing tools without installing.
  `cmake -S . -B object-root/cmake -G Ninja` configures; use
  `-DPython_EXECUTABLE=PATH`, `-DWITH_PAKCS=PATH`, and
  `-DWITH_CURRY_FRONTEND=PATH` to select tools. `make stage` is a thin
  configure/build/install wrapper, preserving the traditional tree.
- `make stage` builds and stages a copy under `install/`. It also compiles
  the Curry library into the installation for the C++ runtime. The modules
  Sprite cannot compile are listed in `unsupported` in
  `CMakeLists.txt`; they get their ICurry and JSON only.
- The products under `curry/lib/**/.curry/sprite-pakcs-3.10.0/` are
  committed artifacts of the pinned current pair; `.json.z` stays derived.
  `make` derives the JSON and keeps valid pins unless you set
  `SPRITE_REBUILD_ICY=1`. After a change to the ICurry
  reader, regenerate the JSON: delete the `.json.z` files and run
  `make stage`.
- `make test` runs the full suite through `tests/run_tests`, which runs
  one process per test file under a memory watchdog (section 10 of
  `tests/README`). Useful forms: `./run_tests 'unit_*.py'` for the unit
  files; `./run_tests -j auto` for a parallel run under the memory budget; `./run_tests --changed` for the files
  that the working-tree changes touch; `./run_tests --fast` for the files
  below five seconds; `./run_tests --list` to see a selection without a
  run; `./run_tests -v FILE` to stream the output of one file (a breakpoint
  needs it). Add `--prepare` on a fresh checkout, after a change to the
  toolchain, and after a change to a runtime header that the generated
  code includes (the include closure of `curryrt/curryrt.hpp`; every compiled
  object is stale then, where a change to a header outside the closure
  rebuilds the runtime library alone), so the shared Curry products are
  compiled before the files run in parallel: under the default a
  test process interprets a stale module and never compiles it.
  `--prepare-only` runs
  the pass alone and exits with its status; CI runs it before the files
  of a C++ shard. The output of each file is in
  `tests/.cache/runner/<backend>/<file>.log`. The default width is
  `auto`: the budget decides how many files run at once, up to the core
  count, on the caps of the calibrated `tests/manifest.json`; `-j 1` runs
  the files one at a time. The `func_*` tests need a PAKCS oracle.
- `make -C docs html` builds the documentation into `object-root/docs/html`.
  It needs a staged install: the Reference pages are generated from the
  installed package, and the command-line pages from the installed tools.
  `docs/source/REPL.rst` describes the REPL (`python -m curry.tools.icy`).
- `make stage CMAKE_ARGS=-DWITH_CCACHE=ccache` enables compiler caching.
  `JOBS=auto` is the default; `make stage JOBS=1` is serial. `make -jN stage`
  overrides the count for one run. CMake `GC=wdgc` (default) or `mps`,
  `CMAKE_BUILD_TYPE=Release` (default) or `Debug`, `TRACE`, `COUNTERS` and
  `GC_WRITE_COUNTERS` select runtime settings. Pinned ICurry rebuilds only
  with `-DSPRITE_REBUILD_ICY=ON`. `pip wheel .` uses scikit-build-core and
  builds distribution `curry`; the import remains `curry`.
- `scripts/setup-dev-machine.sh --prefix DIR` sets up a new machine: the
  apt packages (printed, never installed by the script), PAKCS, a conda
  environment, CMake, `make stage`, and a smoke test. See the page
  "Developer Setup" of the documentation.
- The test drivers cache the output of the Curry front end in
  `tests/.cache/icurry.db`, keyed by the source text, so a repeated run
  compiles only the Curry texts that changed. Set `SPRITE_CACHE_FILE=` (the
  empty string) to run without the cache.
- The C++ backend has a product cache (`SPRITE_PRODUCT_CACHE`, off unless
  it names a directory): `sprite-make`, the background compile of the C++ compiler backend and the prepare
  pass of the test runner look there before they compile a module and
  store the shared object, the generated C++ and the ABI stamp after. The
  runner and `scripts/new-worktree.sh` use `tests/.cache/products`. The
  stamp names the installation as text beside a prefix-free digest of the
  runtime headers the generated code includes and of the flags, plus the
  interface and ICurry fingerprints of its imports, so a
  relocated installation keeps its objects; an object names its imports
  by SONAME, so an entry serves every tree with the same stamp.
- The step that writes `M.icy` writes `M.fint` and `M.icurry` beside it, on
  a cache miss (copies of the front end's files) and on a hit (from the
  cache). Code that needs the type of a symbol reads those copies, never
  the front end's own copy under `.curry/pakcs-3.10.0/`, which can belong to
  another version of the source after a hit. An `.icy` without the two
  files beside it is stale and is converted again. ICurry records the digests
  of its direct imports' `.fint` and `.icurry` interfaces in `.icy.imports`;
  generated C++ and ABI stamps also record imported ICurry for inlining, and
  a missing record or changed import makes the corresponding product stale.
  `make stage` copies the
  interfaces of the installed library beside its `.icy` files, and
  `make overlay` copies them beside the extracted test products and writes
  the `.icy.imports` of an extracted `.icy` that has none. An empty
  interface file means the front end wrote none.
- A functional test runs every goal without value parameters; a goal
  without a signature keeps its class constraints as dictionary parameters,
  which the driver does not count. `func_goal_defaulting.py` pins goal and
  type parity with the PAKCS REPL (`tests/oracle` and `tests/oracle_type`);
  its goldens are committed.
- An installation without a C++ compiler uses LLVM when llvmlite imports.
  With neither backend it runs interpreted and logs one WARNING per process
  (the page "Installing and running without a C++ compiler" of the
  documentation).
- The flag `interpret` of the C++ backend defaults to `new` (`all` on
  Windows). `new` loads current ahead-of-time objects and interprets the
  rest; `all` starts every module interpreted and never opens an AOT
  object; `off` compiles missing objects with the C++ compiler before running and
  errors without one. Background compilation uses `jit:hot,jit_backend:cxx`.
  `sprite-make` and `make stage` always compile.
- The flag `jit` selects compilation of interpreted functions: `hot`
  (default) compiles after `SPRITE_JIT_THRESHOLD` calls (100 by default),
  `eager` compiles at load, and `off` leaves them interpreted. Current AOT
  objects load under `new` and `off` whatever `jit` says. `jit_backend`
  defaults to `auto`: LLVM when llvmlite imports, else the C++ compiler backend (`cxx`) when
  `config.cxx_tool` is available, else interpreter alone with one WARNING
  notice per process. Forced `llvm` and `cxx` error if unavailable;
  install `curry[jit]` or a C++ compiler respectively (the C++ compiler
  backend is unavailable on Windows). LLVM compiles functions in process using llvmlite 0.50 or
  newer (LLVM 22) and `lib/curryrt-helpers.bc`, built with clang through
  `WITH_CLANG`. The C++ compiler backend compiles whole modules in a child
  when their first function becomes hot; eager compilation waits at load. Its
  machinery remains
  in `curry.backends.cxx.tiered` and `src/curryrt/tiered.hpp`; private
  snapshots and publication preserve #173. Hot swaps run at the scheduler
  safepoint. `SPRITE_JIT_DUMP` writes LLVM IR and assembly, for LLVM only.
  Backend and compilation decisions emit INFO messages on the curry logger.
- The C++ backend rotates its queue of alternatives in time mode by
  default (`SPRITE_ROTATION=time:10ms`, a ticker thread, the interpreter
  flag `rotation`) and in step mode (`steps:65536`) under the test runner,
  the benchmark harness and CI, where the exact counters and the order of
  the values of a search must reproduce.
- A goal without a type signature keeps its class constraints. Sprite
  defaults them as the PAKCS REPL does (`Num` and `Integral` to `Int`, `Fractional` and `Floating` to
  `Float`, `Monad` to `IO`, a lone `Data` to `Bool`) and rejects the rest
  with the REPL's sentence. `curry.eval` supplies the dictionaries of such
  a goal; an application, `curry.eval(M.f(1))`, is typed like any term.
  A text goal of `curry.parse` may end in `where x free`; `curry.solve`
  then reports the bindings beside each value. `curry.save(module, path,
  main=...)` writes a program that prints the answers of `main`, or the
  object of the module alone without `main`.

## Conventions

- Every new feature or fixed bug gets a unit test. Mark a known failure
  with `unittest.expectedFailure` instead of deleting the test.
- The modules under `tests/data/curry/typed_expr/` are generated from the
  corpus in `tests/func_typed_expr.py`. Edit the corpus and run
  `python func_typed_expr.py --write` from `tests/`; do not edit the
  modules.
- Work lands on `master`. A topic branch holds the progress of one lane
  until its merge (`--no-ff`) and is deleted, local and on origin, in
  the same step.
- Keep commits free of machine-specific paths and environment details.
