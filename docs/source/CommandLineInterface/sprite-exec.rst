.. highlight:: bash

.. _sprite-exec:

===============
``sprite-exec``
===============

``sprite-exec`` is used to run Curry programs from the command line.  For
simple programs, it suffices to simply pass the filename to this program.  To
run ``Peano.curry`` say::

    cd examples
    PATH=../install/bin:$PATH
    sprite-exec Peano.curry
    S (S O)

The ``PATH`` line is needed only if ``install/bin`` is not already on your
PATH.  The remaining examples on this page assume it is.  ``python -m
curry`` under the Python of the installation is the same program.

The default goal is ``main``.  To specify a different one, use the ``-g``
option; ``-g ''`` loads the module and evaluates nothing::

    sprite-exec Peano.curry -g O
    O

The first run of a program also runs the Curry front end on its module.
That takes a fraction of a second for a small module: ``Peano.curry``
took 0.64 s on its first run and 0.17 s on the second, on the machine of
this text.

For detailed usage, say::

    sprite-exec -h


``sprite-exec`` Manual
======================

.. include:: sprite-exec-usage.rst

Finding Curry Code
==================

If the program contains ``import`` statements, then you may need to set
CURRYPATH in the environment.  This is a colon-delimited list of paths used to
find Curry code.  The path to Sprite's standard Curry library is always added
to this, so importing the ``Prelude``, for instance, does not require setting
CURRYPATH.

.. note::

    Sprite's Curry library can be found in the installation tree under
    ``curry/``.

If the program you want to run resides in a library, then you can tell
``sprite-exec`` to search for it by name by using the ``-m`` option.  Assuming
a BASH-like syntax, one could, for instance, run ``Peano.curry`` from the
repository root with this command::

    CURRYPATH=examples/ sprite-exec -m Peano

Interacting and timing
======================

The option ``-i`` or ``--interact`` opens a Python prompt after the goal
ran, in the namespace of the loaded module.  The symbols of the module are
names there (``add``, ``S``, ``O`` and ``main`` for ``Peano``), and
``import curry`` reaches the API.  Without a module name, ``sprite-exec``
opens the Python prompt at once; ``import curry`` there starts the
interpreter.

The option ``-t`` or ``--time`` suppresses the output of the program and
prints the seconds of the evaluation instead, with no newline; ``--stats``
(below) prints the counters of the whole run.

The Backend
===========

The C++ backend runs a module interpreted until the compiled code is
ready (the interpreter flag ``interpret``), so a program starts at once,
and an installation without a C++ compiler runs every program; see
:doc:`/Installation/WithoutCompiler`.  The ``--backend`` option names the
backend of a run and overrides a ``backend`` flag of
``SPRITE_INTERPRETER_FLAGS``.  The help of ``sprite-exec -h`` names the
default of the installation, which ``configure --with-default-backend``
sets.

See
:ref:`Environment Variables <CommandLineInterface/EnvironmentVariables:Environment Variables>`
for the flags.

Bounding One Alternative
========================

Two interpreter flags bound one alternative, so that a diverging
alternative cannot starve the others.  ``stack_limit`` is the number of
bytes of C stack one evaluation may use.  ``rotation`` is the pace of the
rotation of the queue: time mode, the default, or step mode, in which the
order of the values of a search reproduces between runs.  :ref:`The entry
SPRITE_INTERPRETER_FLAGS <sprite-interpreter-flags>` gives each flag with
its default and its rule, and :ref:`interpreter-flags` tabulates them.
Each flag is set in the environment::

    SPRITE_INTERPRETER_FLAGS=stack_limit:16777216 sprite-exec prog.curry

To pin the order of the values of a search goal, set step mode with the
flag or with ``SPRITE_ROTATION``::

    SPRITE_ROTATION=steps:65536 sprite-exec prog.curry

The test runner and the benchmark harness set step mode themselves, so
the counters of ``--stats`` reproduce exactly between their runs.

Run Statistics
==============

The ``--stats`` option prints one line of ``key=value`` pairs on the standard
error stream when the program ends.  The line comes after the output of the
program, and after the error message when the run fails::

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
    end, the ICurry conversion, code generation, and the C++ compiler.  The
    field is 0 when every file was up to date.

``gc_seconds``
    Seconds the node collector spent in its collections.

``swapped``
    The functions that tiered execution swapped from the interpreter to
    compiled code (the interpreter flag ``interpret``, by default
    ``tiered``: a module without a compiled object is interpreted at once
    and compiled in the background).

``failed_compiles``
    The background compiles of tiered execution that failed; their modules
    stay interpreted, and the failure is logged once per module.

``gc_roots_seconds``, ``gc_trace_seconds``, ``gc_sweep_seconds``, ``gc_registries_seconds``
    Seconds the collections of the node collector spent in each phase: the
    roots (the configurations of the queues and the nodes Python holds),
    the trace from the roots, the block sweep, and the registries (the
    free-variable tables, the generator nodes, the queues and the sets).
    The sum is below ``gc_seconds`` by the small fixed costs of a
    collection and, in the stress mode, by the verifier.

``gc_marked``, ``gc_marked_old``, ``gc_marked_young``
    The nodes the collections marked: all of them, those that the collection
    before had marked as well (old), and those allocated since (young).  The
    old nodes are the live nodes a generational collector would not trace
    in a minor collection.

``gc_configurations_pushed``
    The configurations whose roots the collections pushed.

``gc_queues_destroyed``, ``gc_configurations_destroyed``
    The queues of set functions that no root reached, destroyed by the
    collections, and the configurations destroyed with them.  A
    configuration that a fork or a drop freed is not counted.

``gc_old_redexes``, ``gc_old_slot_writes``, ``gc_old_nodes_written``, ``gc_old_blocks``
    The writes into old nodes between the collections, summed over the
    intervals: the writes of a step into a redex that was old, the other
    pointer writes into an old node (a forward chain shortened in a slot,
    the generator of a free variable, the binding of a variable, the
    string advance of ``writeFile``), the distinct old nodes written (a
    loop that rewrites one old redex at every step counts one node and
    many writes), and the blocks with such a write.  They are the input of
    a write barrier that does not exist yet.  Only a runtime built with
    them (``make GC_WRITE_COUNTERS=1``; they cost a tenth of the
    instructions of a deterministic program) counts them; the default
    build reports 0.  The setting changes the
    runtime headers that generated code includes, so a module is compiled
    with the setting of the installed runtime and compiled again when it
    changes (the ABI stamp): touch ``Make.config`` before ``make
    GC_WRITE_COUNTERS=1 stage`` and again before the plain ``make stage``.
    ``SPRITE_GC_REPORT=1`` prints the counters of every collection (see
    :doc:`EnvironmentVariables`).

Seconds are printed with six decimals.  The same numbers are available in
Python from :func:`curry.stats`, which returns a dict with these keys in this
order; ``str`` of it gives the line above.

Scheduler counters
------------------

A C++ runtime built with ``make COUNTERS=1`` counts what the scheduler does
with its queue of configurations.  The flag changes the runtime library and
its Python bindings only; a plain build has none of the code, and the
generated modules of a plain build serve an instrumented one.  The build
objects do not depend on the variable: touch ``Make.config`` before ``make
COUNTERS=1 stage`` and again before the plain ``make stage``.  The
instrumented runtime costs about one to three percent more instructions and
a word more per node; see the TODO entry for the measurements.

With the counters, ``--stats`` appends these fields after
``gc_old_blocks``, and
:func:`curry.stats` adds the same keys:

``serial_steps``
    Steps taken while the outermost queue held one configuration.  The
    serial fraction, ``serial_steps`` over ``steps``, bounds the gain of a
    thread pool over the queue.

``nested_steps``
    Steps taken inside a set function, whose alternatives run in a queue of
    their own.

``shared_steps``
    Steps whose redex another configuration created.  Every node carries the
    serial number of the configuration whose step allocated it; a redex made
    by an ancestor before a fork, or by a sibling, is work that more than one
    configuration reaches.  The shared-work ratio, ``shared_steps`` over
    ``steps``, bounds the work a design with one copy of the graph per
    alternative would duplicate.  A node built outside the scheduler, such as
    the goal, has no creator and never counts.

``queue_max``
    The largest number of configurations in the outermost queue.

``configurations``, ``failures``, ``failed_steps``
    The configurations of the outermost queue: those that ended with a
    value, a failure, or a fork, and those still in the queue when the
    statistics were read.  ``failures`` and ``failed_steps`` are the ones
    that failed and the steps they took.

``lifetime_median``, ``lifetime_mean``, ``lifetime_max``
    The steps a configuration of the outermost queue took from its creation
    to its end by a value, a failure, or a fork.  The steps of the set
    functions it evaluated count for it.  The median is exact below 1024
    steps; above, it is the lower bound of the power-of-two bucket that
    holds it.

``nested_configurations``, ``nested_lifetime_median``, ``nested_lifetime_mean``, ``nested_lifetime_max``
    The same for the configurations of the queues of set functions.

The counters are per evaluation and summed over the evaluations of the
interpreter, like ``steps``; the maxima take the largest value.  The
benchmark harness keeps the fields of every run and tabulates them with
``run_benchmarks counters FILE`` (see ``tests/README``).

Profiling
=========

The option ``-p`` or ``--profile`` runs the driver under Python's
``cProfile`` profiler.  The rewrite steps of the C++ backend run outside
Python, so the profile shows the driver and not the program; ``--stats``
(above) reports the counters of the program.  To change the sort key, use
``--psort``; the available keys are listed by ``sprite-exec -h``.  The
:doc:`developer notes </DeveloperNotes>` name the use of the option.

Generating Traces
=================

To generate a computation trace, set SPRITE_INTERPRETER_FLAGS as shown here::

    SPRITE_INTERPRETER_FLAGS=trace:true sprite-exec Peano.curry > spritelog

.. note::

  Vim users may wish to :ref:`install <spritelog-highlighting>`
  ``spritelog.vim`` to view the output with syntax highlighting.

