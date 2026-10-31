=============
Release Notes
=============

0.9.0a3 (2026-10-31)
====================

- Windows: the runtime and the bindings build with clang-cl on
  windows-2025 and every module runs interpreted there; wheels for Windows
  x64, CPython 3.11 to 3.15 with the free-threaded 3.14t, which vendor the
  C and C++ runtimes of Visual Studio; the front end's Windows wheel is
  built and gated by the same workflow and ships as ``curry-frontend``
  3.1.0.post2, on PyPI since 2026-10-31.
- A user module named like any module of the installed library is refused
  at import with a message that names both files (#168); the fix of a
  lifted non-linear functional pattern that answered where the oracles
  fail is covered by a direct test (#169).
- Set functions keep the call-time sharing of a caller whose choice escapes
  a capsule: the shortcut that took the side of such a choice through a
  private copy of the spine is gone, and the entry of a capsule no longer
  copies the state behind a set guard; the two-block search of the
  tutorial's betterblocks solver finishes with its six solutions (#172).
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
- The second backend of the JIT is named for what it is: the value ``cxx``
  of ``jit_backend`` (``gxx`` before) compiles the generated C++ of a module
  with the C++ compiler of the installation, g++ or clang++, and the docs
  say "the C++ compiler" where any compiler serves.
- The C++ compiler backend of the JIT leaves the modules of the Curry library to the
  objects of the installation: the private copy of a library source that
  its background compile made was refused by the namesake check, and the
  copy shadowed the library for the compiles that followed, so every
  compile of a process that interpreted the Prelude failed.
  ``sprite-exec --stats`` ends the background compiles before it prints
  its line, so the warning of a failed compile precedes the line.
- A value binding of a big integer keeps its payload across a collection
  (#176); a compiled module reloaded after a reset runs its compiled steps
  (#177); a failed system-library check at import raises ``ImportError``
  with the reason instead of exiting silently (#174).
- Three ways to run a function, over two backends: the flag ``jit``
  (``off``, ``eager``, ``hot``; ``hot`` is the default) and the new flag
  ``jit_backend`` (``auto``, ``llvm``, ``cxx``): LLVM through ``llvmlite``
  when it is installed, else the generated C++ through the C++ compiler, else the
  interpreter alone with one notice.  The value ``tiered`` of ``interpret``
  retires: its live compile is the ``cxx`` backend of the hot tier, the C++ compiler, which
  swaps at a safepoint of the scheduler; ``new`` is the default (``all`` on
  Windows); a current ahead-of-time object always loads.
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
- The background compile of the C++ compiler backend writes its products beside a source only when the
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
