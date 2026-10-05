# Sprite

Sprite is a compiler and runtime for the Curry functional logic language,
based on the Fair Scheme. It has a Python backend and a C++ backend behind a
Python API. The design is described in the author's dissertation:
https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf

## Status (2026)

A refresh is under way on branch `py314` to make Sprite build and run on
current tools. Expect rough edges until the test suite is green again.
Merges to `master` happen at milestones.

## Layout

- `src/python/`: the `curry` Python package (interpreter, compiler, backends).
  `src/python/typecheck/` is the typed boundary: the signature table reads
  the type schemes from the FlatCurry interfaces (`symbol.signature`),
  `defaulting.py` applies the table of the PAKCS REPL to the class
  constraints of a goal, and `goals.py` builds the goal with its
  dictionaries for `curry.eval`, `curry.compile(mode='expr')`, the REPL,
  `sprite-exec -g` and saved modules.
  `src/python/tools/icy/` is the REPL: `python -m curry.tools.icy`, with
  `:load`, `:eval`, `:type`, `:set` and `:quit`.
- `src/cyrt/`: the C++ runtime library.
- `curry/`: the Curry library. `curry/lib/` holds a copy of the library of
  the pinned PAKCS, Sprite's own `Control.SetFunctions`, the license of the
  origin, and the pinned ICurry products. See `curry/README.md`.
- `tests/`: unit tests (`unit_*.py`) and functional tests (`func_*.py`).
  `tests/README` explains the layout, the drivers, and the oracle.
- `docs/`: Sphinx sources.
- `examples/`: runnable examples.
- `conda/`: the scaffold of a conda package for linux-64, not published.
  `conda/README.md` describes the two recipes and the open questions.

## Requirements and policy

- Python 3.14 only. Do not add `six` or compatibility code for older
  Pythons.
- PAKCS 3.4.1 is the pinned front end (Curry to FlatCurry) and the test
  oracle. The pin will be relaxed once the test suite passes. PAKCS itself
  is optional at build time: `configure --with-pakcs ''` with
  `--with-curry-frontend PATH` builds without it, and the pinned release
  then names the intermediate directories.
- Curry is translated to ICurry in two steps: the front end
  (`bin/pakcs-frontend` of PAKCS) writes FlatCurry, and
  `curry.toolchain.flat2icurry`, a Python port of `icurry` 3.1.0, writes
  ICurry. The `icurry` program is an optional alternative, configured with
  `configure --with-icurry` and selected with `SPRITE_CURRY2ICURRY=icurry`
  or `sprite-make --curry2icurry icurry`. Both routes must write
  byte-identical `.icy` files; `tests/README` describes the oracle.
- Other tools: a C++ compiler (g++), GNU make, and Boost headers. jq is not
  needed: Sprite writes compact JSON itself. SWI-Prolog and Haskell Stack
  are needed to build PAKCS itself. GNU time (`/usr/bin/time`) is optional:
  the benchmark harness uses it for the peak memory of a run.
- Sprite needs no GPU.
- `configure` and the Makefiles honour `CC`, `CXX`, `CFLAGS`, `CXXFLAGS`
  and `LDFLAGS` from the environment, so build in a clean environment when
  a conda or cross toolchain is active.

## Build and test

- `./configure` writes `Make.config`. `./configure --check-prereqs` lists
  what is missing. Use `--with-pakcs` and `--with-python` to pick tools.
- `make stage` builds and stages a copy under `install/`. It also compiles
  the Curry library into the installation for both backends. The modules
  Sprite cannot compile are listed in `CURRYLIB_UNSUPPORTED_MODULES` in
  `Make.include`; they get their ICurry and JSON only.
- The `.icy` and `.json.z` files beside the sources under `curry/lib/` are
  committed artifacts of the pinned PAKCS and `icurry` versions. `make`
  derives the JSON from the committed `.icy` and never rebuilds a committed
  `.icy` unless you set `SPRITE_REBUILD_ICY=1`. After a change to the ICurry
  reader, regenerate the JSON: delete the `.json.z` files and run
  `make stage`.
- `make test` runs the full suite through `tests/run_tests`, which runs
  one process per test file under a memory watchdog (section 10 of
  `tests/README`). Useful forms: `./run_tests 'unit_*.py'` for the unit
  files; `./run_tests -j auto --backend both` for a parallel run of both
  backends under the memory budget; `./run_tests --changed` for the files
  that the working-tree changes touch; `./run_tests --fast` for the files
  below five seconds; `./run_tests --list` to see a selection without a
  run; `./run_tests -v FILE` to stream the output of one file (a breakpoint
  needs it). Add `--prepare` on a fresh checkout or after a change to the
  toolchain, so the shared Curry products are compiled before the files
  run in parallel. The output of each file is in
  `tests/.cache/runner/<backend>/<file>.log`. The default width is
  `auto`: the budget decides how many files run at once, up to the core
  count, on the caps of the calibrated `tests/manifest.json`; `-j 1` runs
  the files one at a time. The `func_*` tests need a PAKCS oracle.
- `configure --jobs auto --with-ccache` is the recommended developer setting.
  The parallel build passed its timed trial from a clean tree (see TODO),
  so the default of `--jobs` is `auto`; `--jobs 1` is a serial build.
  `make -jN stage` overrides the configured count for one run.
- `scripts/setup-dev-machine.sh --prefix DIR` sets up a new machine: the
  apt packages (printed, never installed by the script), PAKCS, a conda
  environment, configure, `make stage`, and a smoke test. See the page
  "Developer Setup" of the documentation.
- The test drivers cache the output of the Curry front end in
  `tests/.cache/icurry.db`, keyed by the source text, so a repeated run
  compiles only the Curry texts that changed. Set `SPRITE_CACHE_FILE=` (the
  empty string) to run without the cache.
- The step that writes `M.icy` writes `M.fint` and `M.icurry` beside it, on
  a cache miss (copies of the front end's files) and on a hit (from the
  cache). Code that needs the type of a symbol reads those copies, never
  the front end's own copy under `.curry/pakcs-3.4.1/`, which can belong to
  another version of the source after a hit. An `.icy` without the two
  files beside it is stale and is converted again. `make stage` copies the
  interfaces of the installed library beside its `.icy` files, and
  `make overlay` copies them beside the extracted test products. An empty
  interface file means the front end wrote none.
- A functional test runs every goal without value parameters; a goal
  without a signature keeps its class constraints as dictionary parameters,
  which the driver does not count. `func_goal_defaulting.py` pins goal and
  type parity with the PAKCS REPL (`tests/oracle` and `tests/oracle_type`);
  its goldens are committed.
- `SPRITE_INTERPRETER_FLAGS=backend:cxx` selects the C++ backend. The
  Python backend is the default and suits only small programs.
- A goal without a type signature keeps its class constraints. Sprite
  defaults them as the PAKCS REPL does (`Num` to `Int`, `Fractional` to
  `Float`, `Monad` to `IO`, a lone `Data` to `Bool`) and rejects the rest
  with the REPL's sentence. `curry.eval` supplies the dictionaries of such
  a goal evaluated alone; a call with arguments, `curry.eval(M.f, 1)`, is
  an error until the typed builder lands: compile it from text. A text
  goal of `curry.compile(mode='expr')` may end in `where x free`; its
  values then carry the bindings. `curry.save` needs a goal; pass
  `module_main=False` to save a module without a main program.

## Conventions

- Every new feature or fixed bug gets a unit test. Mark a known failure
  with `unittest.expectedFailure` instead of deleting the test.
- `NOTES` and `TODO` are historical work logs. Verify a claim there before
  you act on it.
- Keep commits free of machine-specific paths and environment details.
