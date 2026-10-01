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
- `curry/`: Curry library sources and per-PAKCS-version overlays.
- `tests/`: unit tests (`unit_*.py`) and functional tests (`func_*.py`).
  `tests/README` explains the layout, the drivers, and the oracle.
- `docs/`: Sphinx sources.
- `examples/`: runnable examples.

## Requirements and policy

- Python 3.14 only. Do not add `six` or compatibility code for older
  Pythons.
- PAKCS 3.4.1 is the pinned front end (Curry to FlatCurry to ICurry). The
  pin will be relaxed once the test suite passes.
- Other tools: a C++ compiler (g++), GNU make, jq, Boost headers, and the
  `icurry` Curry package installed with `cypm`. SWI-Prolog and Haskell
  Stack are needed to build PAKCS itself.
- Sprite needs no GPU.

## Build and test

- `./configure` writes `Make.config`. `./configure --check-prereqs` lists
  what is missing. Use `--with-pakcs` and `--with-python` to pick tools.
- `make stage` builds and stages a copy under `install/`.
- `make test` runs the full suite. For the fast unit tests, run
  `./run_tests 'unit_*.py'` from `tests/`. The `func_*` tests need a PAKCS
  oracle.
- `SPRITE_INTERPRETER_FLAGS=backend:cxx` selects the C++ backend. The
  Python backend is the default and suits only small programs.

## Conventions

- Every new feature or fixed bug gets a unit test. Mark a known failure
  with `unittest.expectedFailure` instead of deleting the test.
- `NOTES` and `TODO` are historical work logs. Verify a claim there before
  you act on it.
- Keep commits free of machine-specific paths and environment details.
