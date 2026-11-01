.. _sprite-exec:

===============
``sprite-exec``
===============

``sprite-exec`` runs a Curry program from the command line. A filename
is enough for a program with ``main``. From ``examples/``, with the
installed tools on PATH::

    sprite-exec Peano.curry
    S (S O)

``python -m curry`` with a program runs the same tool. Without a program,
either command starts the :doc:`Curry REPL </REPL>`.

The default goal is ``main``. To specify a Curry expression, use the ``-g``
option; ``-g ''`` loads the module and evaluates nothing::

    sprite-exec Peano.curry -g O
    O

The expression sees the loaded module and Prelude. For example,
``sprite-exec Peano.curry -g 'O ? S O'`` prints two answers. A trailing
``where x free`` reports bindings, as in the :doc:`REPL </REPL>`.
Each answer prints with ``curry.show`` on its own line. An ``IO ()`` goal
runs its effects and prints no result line; a pure ``()`` still prints
``()``.

A successful run exits with status 0. No value prints
``*** No value found!`` on standard output and exits 2. An evaluation error
prints ``ERROR: msg`` on standard error and exits 1. Suspension prints
``*** Evaluation suspended!`` on standard error and exits 1. A compile
error prints ``ERROR:`` followed by the front end's first error line,
without a machine path and exits 1. These statuses belong to the tools;
Python's ``curry.eval`` returns an empty ``Results`` for no value and
raises evaluation errors.

The first run also runs the Curry front end, under a second for a small
module; later runs skip it. ``sprite-exec -h`` prints the usage:

``sprite-exec`` Manual
======================

.. include:: sprite-exec-usage.rst

Finding Curry code
==================

``CURRYPATH`` is a colon-separated list of directories searched for
modules. The directory of a program given as a file comes first, as in
PAKCS. The Curry library is always on the path, so the modules beside
the program and the Prelude need no ``CURRYPATH``. The installed library
is under ``curry/`` in the installation.

``-m`` names a module instead of a file. From the repository root::

    CURRYPATH=examples/ sprite-exec -m Peano

Interacting and timing
======================

The option ``-i`` or ``--interact`` opens a Python prompt after the goal
ran, in the namespace of the loaded module.  The symbols of the module are
names there (``add``, ``S``, ``O`` and ``main`` for ``Peano``), and
``import curry`` reaches the API.  Without a module name, ``sprite-exec``
starts the Curry REPL.

The option ``-t`` or ``--time`` suppresses the output of the program and
prints the seconds of the evaluation instead, with no newline; ``--stats``
(below) prints the counters of the whole run.

The runtime
===========

The C++ runtime starts a program at once: a module without a current object
runs interpreted. The JIT compiles hot functions when a backend is
available. :doc:`/CompilationOptions` describes the modes and flags; an
installation without a C++ compiler runs every program
(:doc:`/Installation/WithoutCompiler`).

Bounding one alternative
========================

To pin the order of answers, set step mode; the test runner and benchmark
harness do the same::

    SPRITE_ROTATION=steps:65536 sprite-exec Peano.curry

The flags ``stack_limit`` and ``rotation`` are under
:ref:`sprite-interpreter-flags`.

Run statistics
==============

The ``--stats`` option prints one line of ``key=value`` pairs on the standard
error stream when the program ends.  The line comes after the output of the
program and after the error message when the run fails. Timings and
memory use vary between runs. To request the line::

    sprite-exec --stats Peano.curry
    S (S O)
    wall=0.169667 cpu=0.160349 steps=3 forks=0 collections=0 peak_rss=37085184 compile=0.000000 gc_seconds=0.000000 swapped=0 failed_compiles=0 gc_roots_seconds=0.000000 gc_trace_seconds=0.000000 gc_sweep_seconds=0.000000 gc_registries_seconds=0.000000 gc_marked=0 gc_marked_old=0 gc_marked_young=0 gc_configurations_pushed=0 gc_queues_destroyed=0 gc_configurations_destroyed=0 gc_old_redexes=0 gc_old_slot_writes=0 gc_old_nodes_written=0 gc_old_blocks=0

The fields are:

``wall``
    Seconds since the process started (on Linux; elsewhere, since Sprite was
    imported), with the resolution of one clock tick.

``cpu``
    User plus system CPU seconds of the process.  Child processes, such as
    the Curry front end and the C++ compiler, are not included.

``steps``
    The number of rewrite steps.

``forks``
    The number of times a configuration forked at a choice.

``collections``
    The number of collections run by the node collector.

``peak_rss``
    The peak resident set size of the process, in bytes.

``compile``
    Seconds spent in the steps of the compilation pipeline: the Curry front
    end, the ICurry conversion, code generation and the C++ compiler.  The
    field is 0 when every file was up to date.

``gc_seconds``
    Seconds the node collector spent in its collections.

``swapped``
    The functions that the C++ compiler backend swapped from the interpreter to
    compiled code (``jit:hot,jit_backend:cxx`` compiles a module in the
    background after its first hot function). LLVM includes eager and
    cache-linked functions. For the LLVM hot tier it counts posted swaps;
    the scheduler applies them at its next safepoint, so the count can
    include pending swaps.

``failed_compiles``
    The background compiles of the C++ compiler backend that failed; their modules stay interpreted,
    and the failure is logged once per module.

Seconds print with six decimals. :func:`curry.stats` returns the same
fields. The fields of the collector, ``gc_roots_seconds`` to
``gc_old_blocks``, are on every line; a runtime built with ``COUNTERS=1``
appends the scheduler counters. :ref:`developer-run-statistics` describes
both.

Profiling
=========

The option ``-p`` or ``--profile`` runs the driver under Python's
``cProfile`` profiler.  The rewrite steps of the runtime run outside
Python, so the profile shows the driver and not the program; ``--stats``
(above) reports the counters of the program.  To change the sort key, use
``--psort``; the available keys are listed by ``sprite-exec -h``.
