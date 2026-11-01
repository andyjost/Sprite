======
Status
======

This page says what Sprite is today, in one place.

The front end
=============

Sprite translates Curry to FlatCurry with the Curry front end of PAKCS
3.10.0, the pinned release (front end 3.1.0).  The binding optimization of PAKCS is applied
to the FlatCurry file as PAKCS applies it.  Sprite's own port of
``icurry`` 3.3.0 writes the ICurry. The Curry library under ``curry/lib`` is
base 3.4.0 from PAKCS 3.10.0, with Sprite's own ``Control.SetFunctions``,
``Control.Search.SetFunctions`` and ``Sprite.Stream``.
``Control.Search.SetFunctions``, ``Control.Search.Unsafe`` and
``Control.Search.AllValues`` run on Sprite's set functions. Choices in
the body are captured, choices in arguments stay outside and duplicates
are kept. The search strategies they name are accepted and ignored:
every search uses Sprite's scheduler and value order. ``rewriteAll`` and
``rewriteSome`` raise a not-implemented error.
``Control.Search.SearchTree`` is not supported. Sprite provides weak
encapsulation (:ref:`CurryPrimer/Semantics:Set functions`).

The following library modules import, but calling an unimplemented
primitive fails: ``Curry.Compiler.Distribution``, ``Data.IORef``,
``Debug.Trace``, ``System.CPUTime``, ``System.Environment``, ``System.IO``,
``System.IO.Unsafe``, ``Test.Prop``, ``Test.Prop.Types`` and
``Control.Search.SearchTree``.

How code runs
=============

The C++ runtime, ``libcurryrt``, runs a function interpreted, compiled just
in time or compiled ahead of time. The JIT has two backends: LLVM through
llvmlite and C++ through a compiler in a child process. The flags
``interpret``, ``jit`` and ``jit_backend`` choose; :doc:`CompilationOptions`
describes them and the supported platforms.

On Windows x64 the generated modules compile to DLLs with clang-cl of
Visual Studio in a developer prompt (``vcvars64.bat``), ahead of time and
in the C++ tier of the JIT; the library ships compiled and ``interpret``
defaults to ``new`` there as everywhere. A load maps the canonical DLL, and
a publication retires a mapped DLL under a generation name before it
replaces the canonical name. A saved program is a small native launcher
that runs the program with Python. It uses the saving interpreter,
falls back to ``python`` on PATH if needed, and has no runtime DLL
dependency. The Windows workflow gates the native
run; Microsoft's cl is experimental.

LLVM JIT batches persist beside module images as relocatable ``.jit``
objects on supported Unix platforms. Current objects link before evaluation;
``SPRITE_JIT_CACHE`` supplies a fallback for read-only products. Local stages
fill the library cache when llvmlite is present. Wheels omit native JIT
objects and Windows persistence remains future work.

The typed boundary
==================

Sprite reads the type scheme of every symbol from the FlatCurry interface
beside its module.  ``curry.term`` and symbol calls type expressions at construction,
convert Python values by the expected type, supply the class
dictionaries and report a typing failure at construction with
:ref:`the error catalog <typed-errors>`.  A goal without a type signature keeps
its class constraints and :func:`curry.eval`, the REPL, ``sprite-exec
-g`` and ``curry.save`` default them with the table of the PAKCS REPL
(:ref:`goal-defaulting`).  A text goal may end in ``where x free``, and
``curry.solve`` reports the bindings with each value.

The benchmark harness and committed records are described on
:doc:`Performance`.

Known limits
============

* Arithmetic on a free variable of a built-in type suspends the
  evaluation; ``==`` on such a variable in a required position binds it
  through the binding optimization and ``=:=`` always does, as in PAKCS.
* There is no debugger for a nondeterministic computation.
  :doc:`DevelopmentVariables` lists the trace build and runtime counters.
* A value built by a functional pattern stays narrowed. Every later
  comparison resolves it again. Read it through a set function
  (``set1``, ``sortValues``) to resolve it once, as
  :ref:`24: A makefile in Curry <example-24>` does. Issue #86 records the
  measurements.
* Under the C++ backend of the JIT, a module of the same name cannot be
  reloaded from another directory in one process. An edited source is not
  read again in one process. A program shorter than its compile ends
  interpreted with no object written (#179).

What is experimental
====================

* The Memory Pool System collector (``make GC=mps``), optional, off by default; the
  default collector is the mark-and-sweep collector of the block heap.
* The write counters of the collector (``make GC_WRITE_COUNTERS=1``) and
  the scheduler counters (``make COUNTERS=1``): instrumentation for the
  measurements of the generational design and of the parallel-evaluation
  gate, off in the default build.
* The conda recipe under ``conda/``: a scaffold, not published.
* The ICurry cache (``SPRITE_CACHE_FILE``): off by default outside the
  test drivers; CMake ``ENABLE_ICURRY_CACHE=ON`` turns it on (see
  :ref:`CommandLineInterface/EnvironmentVariables:Development Variables`).

Where the plan lives
====================

:doc:`Contributing` links to the tracker and the current milestone.
