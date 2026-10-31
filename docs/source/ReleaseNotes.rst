=============
Release Notes
=============

0.9.0a3 (unreleased)
====================

- Windows: the runtime and the bindings build with clang-cl on
  windows-2025 and every module runs interpreted there; wheels for Windows
  x64, CPython 3.11 to 3.15 with the free-threaded 3.14t, which vendor the
  C and C++ runtimes of Visual Studio; the front end's Windows wheel is
  built and gated by the same workflow and ships with its next release.
- A user module named like any module of the installed library is refused
  at import with a message that names both files (#168); the fix of a
  lifted non-linear functional pattern that answered where the oracles
  fail is covered by a direct test (#169).
- Non-linear functional patterns: the non-strict unification linearizes
  the repeated variables of a pattern and checks them by strict equality
  after the match, as PAKCS does, so ``isJust justZero`` of the PAKCS test
  suite answers where it did not finish before (#165); the inliner keeps
  the calls inside a pattern argument.
- A JIT for the C++ backend: the bytecode of an interpreted function
  compiles to machine code through LLVM (``llvmlite``, the extra
  ``curry[jit]``).  The flag ``jit`` selects ``off``, ``eager`` or ``hot``;
  the hot tier compiles the functions that run and swaps their steps at a
  safepoint of the scheduler.
- A value binding of a big integer keeps its payload across a collection
  (#176); a compiled module reloaded after a reset runs its compiled steps
  (#177); a failed system-library check at import raises ``ImportError``
  with the reason instead of exiting silently (#174).
- ``SPRITE_LOG_FILE`` and ``SPRITE_LOG_LEVEL`` configure a handler on the
  logger ``curry``, which keeps its ``NullHandler`` without them; at INFO
  the package logs its own decisions: how each module runs and why, the
  background compiles, the caches, the front end's runs.
- The README and the documentation state the ways Curry code runs:
  compiled ahead of time, embedded, interpreted, or compiled just in time.

0.9.0a2 (2026-10-27)
====================

- The distribution is named ``curry`` on PyPI: ``pip install --pre curry``
  (the flag while Sprite is in alpha).
  The name ``currylang`` of the first alpha is retired; the import name
  was ``curry`` from the start.
- Wheels for macOS 15 or newer, Apple silicon and Intel, beside the Linux
  wheels; the Curry front end 3.1.0 ships for both as ``curry-frontend``
  3.1.0.post1.
- The current tools are the default: the Curry front end 3.1.0 (the
  package ``curry-frontend`` 3.1.0) with the ``base`` library 3.4.0 of
  PAKCS 3.10.0.  The pair of front end 2.0.0
  and PAKCS 3.4.1 remains accepted.
- The source distribution builds without a Curry front end: the pinned
  products of the library ship with it.
- Unbounded integers: an ``Int`` that overflows the machine word
  promotes to a big integer.
- The Curry preprocessor ``currypp`` is an optional tool found on PATH.
- The tiered compile writes its products beside a source only when the
  compile is done, so a removed directory never holds half-written files
  (#173).  The runtime compiles without strict aliasing (#170).
- Set functions: #133, #134, #139 and #171 fixed.
- A benchmark harness with a community suite of Curry programs.
- The logo: a burst of dust beside the name.

0.9.0a1 (2026-10-24)
====================

The first public alpha, as ``currylang``: Linux wheels for x86-64 and
aarch64 (glibc 2.28 or newer) and CPython 3.11 to 3.15, the free-threaded
3.14 included; the C++ runtime alone, the Python backend having been
removed; the Curry front end 2.0.0 as the separate package
``curry-frontend``.
