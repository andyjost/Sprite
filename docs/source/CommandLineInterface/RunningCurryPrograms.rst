.. highlight:: bash

Running Curry Programs
======================

Using ``sprite-exec``
---------------------

``sprite-exec`` can be used to run Curry programs from the command line.  For
simple programs, it suffices to simply pass the filename to this program.  To
run ``Peano.curry`` say::

    cd examples
    sprite-exec Peano.curry

For detailed usage, say::

    sprite-exec -h

The default goal is ``main``.  To specify a different one, use the ``-g``
option::

    sprite-exec Peano.curry -g O

Finding Curry Code
------------------

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

Profiling
---------

When using the Python backend, it is possible to run a Curry program under
Python's ``cProfile`` profiler.  To do so, simply add the ``-p`` or
``--profile`` option on the command line.  To change the sort key, use
``--psort``.  The available keys are listed by ``sprite-exec -h``.

To run ``Peano.curry`` under the profiler and sort the results by the number of
calls, say::

    sprite-exec Peano.curry --profile --psort=calls

Generating Traces
-----------------

To generate a computation trace, set SPRITE_INTERPRETER_FLAGS as shown here::

    SPRITE_INTERPRETER_FLAGS=trace:true sprite-exec Peano.curry > spritelog

.. note::

  Vim users may wish to :ref:`install <Installation:Syntax Highlighting for
  Spritelog Files>` ``spritelog.vim`` to view the output with syntax
  highlighting.

