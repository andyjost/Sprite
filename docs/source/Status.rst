======
Status
======

This page says what Sprite is today, in one place.  The dated entries of
the file ``TODO`` at the root of the repository hold the record behind each
statement; the code wins over both when they disagree.

The front end
=============

Sprite translates Curry to FlatCurry with the Curry front end of PAKCS
3.4.1, the pinned release.  The binding optimization of PAKCS is applied
to the FlatCurry file as PAKCS applies it.  Sprite's own port of
``icurry`` 3.1.0 writes the ICurry.  The ``icurry`` program is an
optional second route that must write the same bytes.  PAKCS is also the
oracle of the functional tests.  The Curry library is a copy of the
library of that release under ``curry/lib``, with Sprite's own
``Control.SetFunctions``.  See
:ref:`Introduction/CompilationPipeline:Curry to ICurry`.

The two backends
================

The C++ backend is the default (``configure --with-default-backend``).  It
compiles each module to C++ and links it against the runtime library
``libcyrt``, and its runtime also interprets the ICurry of a module from a
bytecode.  The Python backend generates Python and runs the same scheduler
in Python.  It suits small programs.  It is the reference for the
debugging aids of the Python API: the generated code of a function and
the saved form of a module.  Issue #82 plans its retirement.  The C++
backend became the default, and a compiler-free mode exists.  The removal
gate is a month of green nightly runs under the interpreter modes, and it
starts with the first nightly run after the merge.  :func:`curry.save` and
:func:`curry.load` in the Python form, and the examples 03 and 04, belong
to the Python backend until that decision.

The interpreter modes
=====================

The flag ``interpret`` of the C++ backend selects how a module without a
compiled object runs.  ``tiered``, the default, interprets it at once,
compiles it in the background, and swaps its functions to the compiled
code when the object is ready.  ``new`` interprets it and never compiles
it.  ``all`` interprets every module.  ``off`` compiles every module first.
The interpreter takes the same steps as the compiled code and about 1.1 to
1.5 times its time.  An installation without a C++ compiler runs every
program interpreted; see :doc:`Installation/WithoutCompiler`.

The typed boundary
==================

Sprite reads the type scheme of every symbol from the FlatCurry interface
beside its module.  :func:`curry.expr` types an expression before it
builds it, converts Python values by the expected type, supplies the class
dictionaries, and reports a typing failure at construction with
:ref:`the error catalogue <typed-errors>`.  A goal without a type signature keeps
its class constraints, and :func:`curry.eval`, the REPL, ``sprite-exec
-g`` and ``curry.save`` default them with the table of the PAKCS REPL
(:ref:`goal-defaulting`).  A text goal may end in ``where x free``, and
its values carry the bindings.  Open from the plan of epic #48: the
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
``baseline-2026-10-03`` (four suites, both backends and PAKCS).
:doc:`Performance` tabulates the records and names the harness commands.
Two measured facts.  In the memory record of that label ``Tak1`` peaks at
68 MB with the collector and 1009 MB without it.  The rotation check of
the scheduler costs 3 to 5 instructions per completed step over the build
before the ticker (the ``TODO`` entry on K1 and K2).

Known limits
============

* Arithmetic on a free variable of a built-in type suspends the evaluation
  on both backends; ``==`` on such a variable in a required position binds
  it through the binding optimization, and ``=:=`` always does (issue
  #37).
* The Python backend bounds the Python frames of one value with the flag
  ``recursion_limit``, so ``length`` or ``sort`` of a long list ends with
  ``RecursionError`` there; :ref:`the entry of the flag
  <sprite-interpreter-flags>` gives the default and the rule.  The C++
  backend has no such limit below ``stack_limit``.
* There is no debugger for a non-deterministic computation.  The aids are
  the trace flag, ``sprite-exec --stats``, the counters of ``make
  COUNTERS=1``, and the generated code of a function
  (``curry.inspect.getimpl``).
* A name produced by a functional pattern stays narrowed, and every later
  comparison of it resolves the narrowing again; read such a result
  through a set function (issue #86; the note in
  :ref:`CurryPrimer/Syntax:Pattern Matching`).
* The mixed mode of tiered execution has gaps.  A module whose tables
  changed shape after its shim was made stays interpreted, with the
  modules that import it, and one warning says so.  A swapped module keeps
  its registry entry for the life of the process, so a later load of the
  same name from another directory is refused.  A program shorter than its
  compile ends interpreted with no object written.
* The Python backend asserts on a set guard of an enclosing set at the
  root of a configuration (one known failure of the set-function corpus);
  the C++ backend passes it.
* ``show`` of a ``Float`` follows PAKCS on both backends; the ``repr`` of
  a negative ``Float`` node differs between them.

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
  test drivers; ``configure --cache`` turns it on (see
  :ref:`CommandLineInterface/EnvironmentVariables:Development Variables`).

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
* #30, the future of the Python backend.
* #40, developer velocity.
* #48, the typed boundary between Python and Curry.
* #67, Phase 3: optimizer passes, native workers, ticker rotation, pointer
  tagging.
* #87, an array IR example and the bulk boundary.
