=============
Release Notes
=============

0.9.0a3 (2026-11-01)
====================

- Implement ``System.IO`` handles and current Python standard streams,
  enabling ``Debug.Trace.traceIO``, plus primitives for the CPM packages ``directory``
  and ``process``. ``exitWith`` raises catchable ``SystemExit`` in the API.
- Reuse typed Python terms, copy their graphs for evaluation, and format
  goal text on demand. Warm CPU measurements reduce a small interpreted
  call from 402 to about 270 microseconds and lesson 21's overload call
  from 18.3 to about 4.3 milliseconds. Nested ``Just`` construction is
  linear (#181): a depth-128 chain falls from 2.93 seconds to about
  9 milliseconds.
- Convert ground results in the C++ bindings, preserving Python value types
  and representations. Measured CPU conversion time falls from 7.39 ms to
  11.4 us for 1000 Ints and from 2.18 ms to 2.11 us for a 300-character
  String; lesson 24's complete query falls from 978 us to 635 us.
  Cached expression-symbol tables also remove converter-construction growth
  after repeated parses.
- Add the qualified-name primitive registry and the primitives of
  ``Curry.Compiler.Distribution``, ``System.CPUTime``, ``System.Environment``
  and ``Data.IORef``, including registered Python implementations for process
  arguments, the program name and hostname.
- Implement the nine ``System.IO.Unsafe`` primitives, including
  configuration-sensitive variable observations, arbitrary term read/show,
  and ``spawnConstraint`` with the suspension rule of ``&``. Strong-search
  operations still await an owner decision.
- Every module of the Curry library ships compiled. An external function
  without a primitive in the runtime raises ``not implemented`` at its call;
  before, eight modules failed at import.
- The front end uses ``C.UTF-8`` when the selected locale is not UTF-8,
  so non-ASCII Curry source also compiles under C and POSIX locales.
- Local CPM projects add their source directories and installed packages
  to ``curry.path`` after ``CURRYPATH`` and before the installed library;
  ``SPRITE_CPM_PATH=0`` disables discovery.
- Windows: Sprite discovers Visual Studio with ``vswhere`` and captures
  the developer environment of ``vcvars64.bat`` for clang-cl. AOT builds,
  the C++ JIT and saved-program launchers no longer need a developer prompt.

- ``curry.solve`` reports every held variable used in the goal, including
  unnamed variables under display names such as ``_a``.

- The JIT compiles interpreted functions through LLVM (``llvmlite``, the
  new extra ``"curry[jit]"``) or the C++ compiler. ``jit`` selects
  ``off``, ``eager`` or ``hot`` (default); ``jit_backend`` selects
  ``auto``, ``llvm`` or ``cxx``. Hot swaps run at a scheduler safepoint.
  Without a backend the process says so once in its log, at INFO. Every
  wheel carries the bitcode of the JIT helpers, which the distributions
  gate requires.
  ``interpret:tiered`` is retired; ``interpret:new`` is the default
  on every platform and current ahead-of-time objects still load. A
  background compile of the C++ backend whose thread cannot start (a
  limit on the tasks of the user) is reported as a failed compile; the
  module stays interpreted and the evaluation goes on.
- The cached code of a function links at its first call, from one native
  object per function in the envelope; a start reads the index alone. CI
  fills the library's cache in one job (``SPRITE_STAGE_JIT_CACHE=0`` skips
  the fill of a stage).
- The LLVM cache uses smaller module-local symbols and per-function zlib
  payloads (``SPRTJIT4``). Cached calls can resolve between hot optimizer
  batches; pinned cache files close after resolution or image detach.
- LLVM JIT batches persist as relocatable ``.jit`` objects beside module
  images, resolve on first use on a warm start and use
  ``SPRITE_JIT_CACHE`` for read-only products. Local stages fill the library
  cache; wheels omit machine-specific objects. Windows persistence follows
  separately.

- Module images replace module JSON products. Translation and C++ emission
  read ICurry text; read-only directories and text modules use private images.
  ``sprite-make --image`` is the default target; the JSON options are removed.
- Image preparation constructs imported optimizer declarations on demand.
  In a local three-run comparison, warm compile CPU medians fell from
  0.302 to 0.282 s for Fib, 0.357 to 0.340 s for QueensSet, and 0.307 to
  0.264 s for an expression (about 5 to 14 percent); image bodies and
  optimization remain enabled.

- Windows: the runtime and the bindings build with clang-cl, and so do the
  generated modules, as DLLs, ahead of time and in the hot and eager C++
  tiers; ``interpret`` defaults to ``new`` on every platform. A load maps
  the canonical DLL, so a read-only installation imports compiled modules;
  a publication retires a mapped DLL under a generation name, and the
  stage and the wheel gates reject such files. A saved program
  (``curry.save(main=...)``) is a small native launcher that runs the
  program with Python. It uses the saving interpreter,
  falls back to ``python`` on PATH if needed and has no runtime DLL
  dependency. Wheels support Windows x64 and CPython 3.11 to
  3.15, including free-threaded 3.14t, and ship the compiled library and
  the C and C++ runtime libraries of Visual Studio. The front end's
  Windows wheel, ``curry-frontend`` 3.1.0.post2, is on PyPI since
  2026-10-31.
- A user module named like any module of the installed library is refused
  at import with a message that names both files (#168). A
  lifted non-linear functional pattern no longer answers where PAKCS and
  KiCS2 give no value (#169).
- Set functions keep the call-time sharing of a caller whose choice escapes
  a capsule: the shortcut that took the side of such a choice through a
  private copy of the spine is gone and the entry of a capsule no longer
  copies the state behind a set guard; the two-block search of the
  tutorial's betterblocks solver finishes with its six solutions (#172).
- Non-linear functional patterns: the non-strict unification linearizes
  the repeated variables of a pattern and checks them by strict equality
  after the match, as PAKCS does, so ``isJust justZero`` of the PAKCS test
  suite answers where it did not finish before (#165).
- A module is translated once into a binary image that the C++ runtime
  reads directly, with the optimizer passes run at translation time: the
  interpreted start of the Prelude falls from 0.73 s to 0.04 s. The images
  of the library are products of the stage and ship in the wheels; an
  installation whose directory is read-only uses a private image;
  compiled products carry receipts of the translation that made them
  (#175).
- The second backend of the JIT is named for what it is: the value ``cxx``
  of ``jit_backend`` (``gxx`` before) compiles the generated C++ of a module
  with the C++ compiler of the installation, g++ or clang++ and the docs
  say "the C++ compiler" where any compiler serves.
- Background compiles no longer fail in a process that interpreted the
  Prelude: library modules run from the installation's objects.
  ``sprite-exec --stats`` waits for background C++ compiles, so a compile
  warning precedes its line.
- A value binding of a big integer keeps its payload across a collection
  (#176); a compiled module reloaded after a reset runs its compiled steps
  (#177); a failed system-library check at import raises ``ImportError``
  with the reason instead of exiting silently (#174).
- ``SPRITE_LOG_FILE`` and ``SPRITE_LOG_LEVEL`` configure a handler on the
  logger ``curry``, which keeps its ``NullHandler`` without them; at INFO
  the package logs its own decisions: how each module runs and why, the
  background compiles, the caches, the front end's runs.
- The README and the documentation state the ways Curry code runs:
  compiled ahead of time, embedded, interpreted or compiled just in time.

0.9.0a2 (2026-10-27)
====================

- The distribution is named ``curry`` on PyPI: ``pip install --pre curry``
  (the flag while Sprite is in alpha).
  The name ``currylang`` of the first alpha is retired; the import name
  was ``curry`` from the start.
- Wheels for macOS 15 or newer on arm64 and x86-64, beside the Linux
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
