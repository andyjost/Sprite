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

The ``PATH`` line is needed only if ``install/bin`` is not already on your
PATH.  The remaining examples on this page assume it is.

The default goal is ``main``.  To specify a different one, use the ``-g``
option::

    sprite-exec Peano.curry -g O

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

Selecting a Backend
===================

Sprite has two backends.  The Python backend is the default.  It suits small
programs.  The C++ backend is faster and suits larger programs.  To select
it, set ``SPRITE_INTERPRETER_FLAGS`` in the environment::

    SPRITE_INTERPRETER_FLAGS=backend:cxx sprite-exec prog.curry

The ``--backend`` option selects the backend without the environment variable
and overrides a ``backend`` flag set there::

    sprite-exec --backend cxx prog.curry

See
:ref:`Environment Variables <CommandLineInterface/EnvironmentVariables:Environment Variables>`
for the other flags.

Bounding One Alternative
========================

Two flags keep one alternative from starving the others.  On the Python
backend, ``step_budget`` sets the number of rewrite steps one alternative gets
before the next one runs.  The default is 2048::

    SPRITE_INTERPRETER_FLAGS=step_budget:65536 sprite-exec prog.curry

``None`` disables the step-budget rotation.  Rotation on residuation and on
Python stack overflow still occurs.  An alternative that overflows the Python
stack runs again after the others.  When it overflows again without progress,
it is dropped, and its error is reported after the others have run.

On the C++ backend, ``stack_limit`` sets the number of bytes of C stack one
evaluation may use.  The default is 4194304.  When an alternative reaches the
limit, the other alternatives run.  An alternative that cannot proceed within
the limit is dropped, and its error is reported after the others have run.
``None`` disables the guard.  A limit larger than the stack of the thread is
clamped to that stack, less a margin of 1 MiB.

Run Statistics
==============

The ``--stats`` option prints one line of ``key=value`` pairs on the standard
error stream when the program ends.  The line comes after the output of the
program, and after the error message when the run fails::

    sprite-exec --stats Peano.curry
    S (S O)
    wall=0.129943 cpu=0.129125 steps=3 forks=0 collections=0 peak_rss=36773888 compile=0.000000

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
    The number of collections run by the node collector of the C++ backend.
    The Python backend reports 0.

``peak_rss``
    The peak resident set size of the process, in bytes.

``compile``
    Seconds spent in the steps of the compilation pipeline: the Curry front
    end, the ICurry conversion, code generation, and the C++ compiler.  The
    field is 0 when every file was up to date.

Seconds are printed with six decimals.  The same numbers are available in
Python from :func:`curry.stats`, which returns a dict with these keys in this
order; ``str`` of it gives the line above.

Profiling
=========

When using the Python backend, it is possible to run a Curry program under
Python's ``cProfile`` profiler.  To do so, simply add the ``-p`` or
``--profile`` option on the command line.  To change the sort key, use
``--psort``.  The available keys are listed by ``sprite-exec -h``.

To run ``Peano.curry`` under the profiler and sort the results by the number of
calls, say::

    sprite-exec Peano.curry --profile --psort=calls

Generating Traces
=================

To generate a computation trace, set SPRITE_INTERPRETER_FLAGS as shown here::

    SPRITE_INTERPRETER_FLAGS=trace:true sprite-exec Peano.curry > spritelog

.. note::

  Vim users may wish to :ref:`install <spritelog-highlighting>`
  ``spritelog.vim`` to view the output with syntax highlighting.

