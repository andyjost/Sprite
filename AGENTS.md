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
- `make stage` builds and stages a copy under `install/`.
- The `.icy` and `.json.z` files beside the sources under `curry/lib/` are
  committed artifacts of the pinned PAKCS and `icurry` versions. `make`
  derives the JSON from the committed `.icy` and never rebuilds a committed
  `.icy` unless you set `SPRITE_REBUILD_ICY=1`. After a change to the ICurry
  reader, regenerate the JSON: delete the `.json.z` files and run
  `make stage`.
- `make test` runs the full suite. For the fast unit tests, run
  `./run_tests 'unit_*.py'` from `tests/`. The `func_*` tests need a PAKCS
  oracle.
- The test drivers cache the output of the Curry front end in
  `tests/.cache/icurry.db`, keyed by the source text, so a repeated run
  compiles only the Curry texts that changed. Set `SPRITE_CACHE_FILE=` (the
  empty string) to run without the cache.
- `SPRITE_INTERPRETER_FLAGS=backend:cxx` selects the C++ backend. The
  Python backend is the default and suits only small programs.

## Conventions

- Every new feature or fixed bug gets a unit test. Mark a known failure
  with `unittest.expectedFailure` instead of deleting the test.
- `NOTES` and `TODO` are historical work logs. Verify a claim there before
  you act on it.
- Keep commits free of machine-specific paths and environment details.
