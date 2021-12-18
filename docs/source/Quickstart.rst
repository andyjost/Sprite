==========
Quickstart
==========

.. toctree::

For the impatient among us, this guide demonstrates some basic capabilities of
Sprite.  It shows how to install Sprite; run Curry programs from the command
line; and load modules, build expressions, evaluate code, and convert values
using the Python API.

Quick Build
===========

Ensure Python, PAKCS, and icurry are in your PATH, and that their versions are
:ref:`compatible <Introduction/ExternalSoftware:Compatibility>` with Sprite.
Then configure and stage Sprite:

.. code-block:: bash

    ./configure
    make stage

This creates an installation of Sprite at ``$ROOT/install``, where ROOT refers
the Sprite repository root.  To run the examples below prepend
``$ROOT/install/bin`` to your PATH.

Running Curry Programs
======================

Curry programs can be run with :ref:`sprite-exec`.  To try this, go to the
``examples/`` directory.  You will there find a file named ``Peano.curry``
containing the following:

.. code-block:: haskell

    data Nat = O | S Nat
    add :: Nat -> Nat -> Nat
    add O n = n
    add (S n) m = S (add n m)

    main :: Nat
    main = add (S O) (S O)

To evaluate this program, say:

.. code-block:: bash

    % sprite-exec Peano.curry
    S (S O)

Sprite runs goal ``main`` by default.  You can use ``-g`` to specify a
different one.

Python API Quickstart
=====================

To begin, start Python:

.. code-block:: bash

    % python

.. important::

    Ensure you are using ``$ROOT/install/bin/python``, as this configures
    PYTHONPATH and other environment variables.

To import Sprite, say:

    >>> import curry

Use ``dir`` and ``help`` to explore package :mod:`curry` for yourself.  To list
the functions, submoudles, and other objects provided by Sprite, say:

    >>> dir(curry)

To read the help documentation, pass any of these objects to the ``help``
command.  Take this opportunity to say:

    >>> help(curry)

.. tip::

    A basic familiarity with Python is assumed.  The `Python Tutorial`_
    provides an excellent primer.

Importing Curry
---------------

To load a Curry module in to Python, import it relative to the virtual package
:mod:`curry.lib`:

    >>> from curry.lib import Prelude

This statement uses CURRYPATH to search for Curry files.  Sprite automatically
appends its path to system Curry libraries, such as the Prelude.  The CURRYPATH
is reflected in Python as the list variable :data:`curry.path`.  Updating this
modifies the search path dynamically.

To load ``Peano``, first add the current directory, ``examples/``, to the
search path and then import it:

    >>> curry.path.insert(0, '.')
    >>> from curry.lib import Peano

Accessing Symbols
-----------------

Curry symbols are constructor and function names (but not type names).  The
public symbols of ``Peano`` are exposed as attributes of the module object:

    >>> Peano.S
    <curry constructor 'Peano.S'>
    >>> Peano.add
    <curry function 'Peano.add'>

Not all Curry symbols are valid Python identifiers.  Use ``getattr`` to access
these:

    >>> getattr(Prelude, '++')
    <curry function 'Prelude.++'>

You may also find symbols by their full names using :func:`curry.symbol`:

    >>> curry.symbol('Prelude.++')
    <curry function 'Prelude.++'>


Building and Evaluating Goals
-----------------------------

To build a goal, use :func:`curry.compile` with mode ``'expr'``:

    >>> goal = curry.compile(
    ...     'add (S O) (S O)', mode='expr', exprtype='Nat', imports=[Peano]
    ...   )

To evaluate the goal, use :func:`curry.eval`.

    >>> values = curry.eval(goal)

Since Curry evaluations can produce multiple values, the result is an `iterable
<https://wiki.python.org/moin/Iterator>`_ object.  To print one value, say:

    >>> print(next(values))
    S (S O)

To place the values into a list, say:

    >>> values = list(curry.eval(goal))

To iterate over the values, write a `for
<https://docs.python.org/3/reference/compound_stmts.html#the-for-statement>`_
loop:

    >>> for value in curry.eval(goal):
    ...   # your code here; use break to terminate evaluation.

To partially evaluate an expression, simply discard the iteratable before it is
exhaused.

.. tip::

    When the number of values is known and you wish to capture them all, use
    an unpacking assignment.  For example:

        >>> result, = curry.eval(goal)

    Note the comma following ``result``.  This construct completely evaluates
    the goal, checks that it produced exactly one result, and binds that to
    ``value``.  If multiple values are expected, use a comma-separated list:

        >>> a,b = curry.eval(goal_with_two_values)

Building Curry Expressions in Python
------------------------------------

:func:`curry.compile` invokes the Curry frontend, which can be quite slow (see
:ref:`important-notes`).  To build expressions more quickly, use
:func:`curry.expr`.

    >>> goal2 = curry.expr(Peano.add, [Peano.S, Peano.O], [Peano.S, Peano.O])
    >>> print(next(curry.eval(goal2)))
    S (S O)

.. warning::

  Since it bypasses the frontend, :func:`curry.expr` can produce ill-typed
  expressions.  Its use represents a compromise between safety and practicality
  (see :ref:`important-notes`).  Evaluating an ill-typed expression results in
  undefined behavior, so use caution.

To build an expression containing a choice, use ``Prelude.?``:

    >>> print(curry.expr(getattr(Prelude, '?'), 1, 2))
    (?) 1 2

To build an expression containing a free variable, use :class:`curry.free`:

    >>> print(curry.expr(curry.free()))
    _0

To build a cons-style list, either use the symbols ``Prelude.:`` and
``Prelude.[]`` directly or employ :class:`curry.cons` and :data:`curry.nil`:

    >>> print(curry.expr(curry.cons(1, curry.nil)))
    [1]
    >>> print(curry.expr(curry.cons(1, 2, 3, curry.nil)))
    [1, 2, 3]

Nonlinear expressions contain a cycles or shared subexpressions.  To build a
nonlinear expression, define a named subexpression and refer to it with
:class:`curry.ref`.  For example, the following constructs ``let a=(1:a) in
a``:

    >>> cons, ref = curry.cons, curry.ref
    >>> curry.expr(ref('a'), a=cons(1, ref('a')))
    <: <Int 1> ...>

Converting Values
-----------------

To convert Curry values to Python, use :func:`curry.topython`:

    >>> cy123 = curry.expr([1, 2, 3])
    >>> cy123
    <: <Int 1> <: <Int 2> <: <Int 3> <[]>>>>
    >>> py123 = curry.topython(cy123)
    >>> py123
    [1, 2, 3]
    >>> type(py123)
    <type 'list'>

You may also instruct :func:`curry.eval` to convert results as they are
generated:

    >>> append = getattr(Prelude, '++')
    >>> goal3 = curry.expr(append, [1], [2,3])
    >>> next(curry.eval(goal3, converter='topython'))
    [1, 2, 3]

Saving Compiled Curry
---------------------

Use :func:`curry.save` to save compiled Curry code to a file:

    >>> curry.save(Peano, 'Peano.py', goal='main')

Use this to see how Sprite compiles Curry into Python.

If a goal was provided, as shown above, the file can be run as a standalone
application:

.. code-block:: bash

    % chmod +x Peano.py
    % ./Peano.py
    S (S O)

To import the compiled module into Python, either import is as a regular Python
module or use :func:`curry.load`:

    >>> import sys
    >>> sys.path.insert(0, '.')
    >>> import Peano

or

    >>> Peano = curry.load('Peano.py')

Both methods add ``Peano`` to :data:`curry.modules`.

.. _Python Tutorial: https://docs.python.org/3/tutorial/

