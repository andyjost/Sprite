======
Status
======

This page says what Sprite is today, in one place.  The code wins when
this page disagrees with it.

The front end
=============

Sprite translates Curry to FlatCurry with the Curry front end of PAKCS
3.10.0, the pinned release (front end 3.1.0).  The binding optimization of PAKCS is applied
to the FlatCurry file as PAKCS applies it.  Sprite's own port of
``icurry`` 3.3.0 writes the ICurry.  The ``icurry`` program is an
optional second route that must write the same bytes.  PAKCS is also the
oracle of the functional tests. The Curry library under ``curry/lib`` is
base 3.4.0 from PAKCS 3.10.0, with Sprite's own ``Control.SetFunctions``,
``Control.Search.SetFunctions``, and ``Sprite.Stream``. The same sources
serve front end 2.0.0 with PAKCS
3.4.1 and front end 3.1.0 with PAKCS 3.10.0. See
:ref:`Introduction/CompilationPipeline:Curry to ICurry`.

The search library
==================

``Control.Search.SetFunctions``, ``Control.Search.Unsafe``, and
``Control.Search.AllValues`` run over the native weak capsules. The facade
shares ``Control.SetFunctions.Values a = Values [a]`` with Sprite's extension.
Body choices are captured, argument choices stay outside, and duplicates
are retained. Strategies and DFS names are advisory: all use Sprite's fair
scheduler and value order. Unsafe and AllValues upstream describe strong
encapsulation; Sprite does not enumerate expression free variables inside.
``rewriteAll`` and ``rewriteSome`` report not implemented when called,
since capsules cannot suppress outside binding demands.
``Control.Search.SearchTree`` remains unsupported, pending strong search.

The backend
===========

The C++ backend is the one runtime.  Its runtime library ``libcurryrt``
runs compiled code and interprets ICurry bytecode, including installations
without a compiler.  See :doc:`Installation/WithoutCompiler`.

The interpreter modes
=====================

The flag ``interpret`` defaults to ``new``: current ahead-of-time objects
load, and other modules start interpreted. ``all`` starts every module
interpreted and never opens an ahead-of-time object; it is the Windows
default. ``off`` compiles missing objects before running.

The flag ``jit`` defaults to ``hot``. Interpreted functions compile after
100 calls (``SPRITE_JIT_THRESHOLD``), with swaps at the scheduler's
safepoint. ``eager`` compiles at module load; ``off`` keeps the interpreter.
``jit_backend:auto`` selects LLVM when llvmlite imports, else gxx when a
C++ compiler is available, else the interpreter alone with one warning per
process. Forced ``llvm`` and ``gxx`` report unavailable prerequisites as
errors. LLVM compiles functions in process; gxx compiles whole modules in
a child, preserving the private-copy and publication protocol of #173.
``interpret:tiered`` is retired: use ``jit:hot,jit_backend:gxx``.
See :doc:`Installation/WithoutCompiler`.

The typed boundary
==================

Sprite reads the type scheme of every symbol from the FlatCurry interface
beside its module.  ``curry.term`` and symbol calls type expressions at construction,
convert Python values by the expected type, supply the class
dictionaries, and report a typing failure at construction with
:ref:`the error catalogue <typed-errors>`.  A goal without a type signature keeps
its class constraints, and :func:`curry.eval`, the REPL, ``sprite-exec
-g`` and ``curry.save`` default them with the table of the PAKCS REPL
(:ref:`goal-defaulting`).  A text goal may end in ``where x free``, and
``curry.solve`` reports the bindings with each value.  Open from the plan of epic #48: the
schemes as metadata of the generated modules instead of the interface
reads, the specialization of a saturated method call, and a random
harness over the engine.

The performance record
======================

The committed records are under ``tests/data/curry/benchmarks/results``,
one JSON Lines file per suite and run.  The record of the C++ backend
after Phase 2 of the performance program is the label
``phase2-2026-10-04``, in the files ``phase2-2026-10-04-throughput.jsonl``
and ``phase2-2026-10-04-memory.jsonl``: the nightly set of ten programs,
three repetitions.  The baseline before the program is the label
``baseline-2026-10-03`` (four suites, Sprite and PAKCS).  The current
record is ``phase3-2026-10-10`` (the inliner, the known-constructor rule
and the step-mode rotation; throughput and memory, with instruction
counts), and ``apps-2026-10-06`` holds the applications suite;
``tests/data/curry/benchmarks/results/README.md`` describes each.
:doc:`Performance` tabulates the records and names the harness commands.
Two measured facts.  In the memory record of that label ``Tak1`` peaks at
68 MB with the collector and 1009 MB without it.  The rotation check of
the scheduler costs 3 to 5 instructions per completed step over the build
before the ticker.

Known limits
============

* Arithmetic on a free variable of a built-in type suspends the
  evaluation; ``==`` on such a variable in a required position binds it
  through the binding optimization, and ``=:=`` always does (issue #37).
* There is no debugger for a non-deterministic computation.  The aids are
  ``sprite-exec --stats``, the counters of ``make COUNTERS=1``, and the
  generated code of a function (``curry.inspect.getimpl``).
* A name produced by a functional pattern stays narrowed, and every later
  comparison of it resolves the narrowing again; read such a result
  through a set function (issue #86; the note in
  :ref:`CurryPrimer/Syntax:Pattern Matching`).
* The gxx hot tier has gaps.  A swapped module keeps
  its registry entry for the life of the process, so a later load of the
  same name from another directory is refused, before the object is
  opened.  :func:`curry.load` of the object of a module whose background
  compile runs waits for the compile; an explicit load adopts the object
  over the live interpreted tables.  An edited source
  is not read again in one process: the import says so, and the swap
  refuses an object compiled from the edited file.  A program shorter
  than its compile ends interpreted with no object written.
* ``show`` of a ``Float`` follows PAKCS.

What is experimental
====================

* The Memory Pool System collector (``make GC=mps``), behind a gate; the
  default collector is the mark-and-sweep collector of the block heap.
* The write counters of the collector (``make GC_WRITE_COUNTERS=1``) and
  the scheduler counters (``make COUNTERS=1``): instrumentation for the
  measurements of the generational design and of the parallel-evaluation
  gate, off in the default build.
* The conda recipe under ``conda/``: a scaffold, not published.
* The ICurry cache (``SPRITE_CACHE_FILE``): off by default outside the
  test drivers; CMake ``ENABLE_ICURRY_CACHE=ON`` turns it on (see
  :ref:`CommandLineInterface/EnvironmentVariables:Development Variables`).
* The JIT of the C++ backend (the flag ``jit``, the extra ``curry[jit]``,
  issue #65): the bytecode of a function to machine code through LLVM,
  eagerly or by call count, on Linux, macOS arm64 and Windows; merged on
  2026-10-30, hot by default.

Where the plan lives
====================

The tracker is the issue list of the repository on GitHub.  The milestone
is number 1, "Sprite resuscitated"; its page lists the open items.  The
epics are these issues:

* #6, measurement infrastructure.
* #11, CI and test-suite speed.
* #14, interactive latency.
* #19, throughput of the C++ runtime.
* #24, memory management.
* #28, parallel evaluation, behind a gate.
* #30 and #82, closed: the Python backend was removed on 2026-10-24.
* #40, developer velocity.
* #48, the typed boundary between Python and Curry.
* #67, Phase 3: optimizer passes, native workers, ticker rotation, pointer
  tagging.
* #87, an array IR example and the bulk boundary.
