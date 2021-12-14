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

.. note::

    The examples below assume ``$ROOT/install/bin`` was prepended to the PATH.
    ROOT refers the Sprite repository root.

Running Curry Programs
======================

Curry programs can be run with ``sprite-exec``.  To try this, go to
the ``examples/`` directory.  You will there find a file named ``Peano.curry``
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

Use ``dir`` and ``help`` to explore ``curry`` for yourself.  To list the
functions, submoudles, and other objects provided by Sprite, say:

    >>> dir(curry)

To read the help documentation, pass any of these objects to the ``help``
command.  Take this opportunity to say:

    >>> help(curry)

.. tip::

    A basic familiarity with Python is assumed.  The `Python Tutorial`_
    provides an excellent primer.

Importing Curry
---------------

To import a Curry module, import it relative to the virtual package
``curry.lib``:

    >>> from curry.lib import Prelude

This statement uses CURRYPATH to search for Curry files.  Sprite automatically
appends its path to system Curry libraries, such as the Prelude.  The CURRYPATH
is reflected in Python as the list variable ``curry.path``.  Updating this
modifies the search path dynamically.

The examples below rely on the ``Peano`` module defined in
``examples/Peano.curry``.  Update the search path and import it as follows:

    >>> curry.path.insert(0, 'examples/')
    >>> from curry.lib import Peano

Accessing Symbols
-----------------

Public symbols appear as attributes of the module:

    >>> Peano.S
    <curry constructor 'Peano.S'>
    >>> Peano.add
    <curry function 'Peano.add'>

Use ``getattr`` to look up a symbol whose name is not a valid Python
identifier:

    >>> getattr(Prelude, '++')
    <curry function 'Prelude.++'>

You may also use ``curry.symbol`` to look up a symbol by its full name:

    >>> curry.symbol('Prelude.++')
    <curry function 'Prelude.++'>


Building and Evaluating Goals
-----------------------------

To build a goal, use ``curry.compile`` with mode ``'expr'``:

    >>> goal = curry.compile('add (S O) (S O)', mode='expr', import=[Peano])

To evaluate the goal, use ``curry.eval``.

    >>> values = curry.eval(goal)

Since Curry evaluations can produce multiple values, ``values`` is an `iterable
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

To partially evaluate a Curry expression, simply discard the iteratable before
it is exhaused.

.. tip::

    When the number of values is known and you wish to capture them all, use
    an unpacking assignment.  For example:

        >>> values, = curry.eval(goal)

    Note the comma following ``values``.  This construct completely evaluates
    the goal, checks that it produces exactly one result, and binds that to
    ``value``.  If multiple values are expected, use a comma-separated list:

        >>> a,b = curry.eval(goal_with_two_values)

Building Curry Expressions in Python
------------------------------------

``curry.compile`` invokes the Curry frontend, which can be quite slow.  To
build expressions more quickly, use ``curry.expr``.

    >>> goal2 = curry.expr(Peano.add, [Peano.S, Peano.O], [Peano.S, Peano.O])
    >>> print(next(curry.eval(goal2)))
    S (S O)

.. warning::

  ``cury.expr`` bypasses the frontend, and so can produce ill-typed
  expressions.  Use caution, since evaluating one results in undefined
  behavior.

To build an expression containing a choice, use ``Prelude.?``:

    >>> print(curry.expr(getattr(Prelude, '?'), 1, 2))
    (?) 1 2

To build an expression containing a free variable, use ``curry.free``:

    >>> print(curry.expr(curry.free()))
    _0

To build a cons-style list, use ``curry.cons`` and ``curry.nil``:

    >>> print(curry.expr(curry.cons(1, curry.nil)))
    [1]

To build an expression containing a cycle or shared subexpression, supply a
named subexpression and refer to it with ``curry.ref``.  For example, the
following constructs ``let a=(1:a) in a``:

    >>> curry.expr(curry.ref('a'), a=curry.cons(1, curry.ref('a')))
    <: <Int 1> ...>

Converting Values
-----------------

To convert Curry values to Python, use ``curry.topython``:

    >>> cy123 = curry.expr([1, 2, 3])
    >>> cy123
    <: <Int 1> <: <Int 2> <: <Int 3> <[]>>>>
    >>> py123 = curry.topython(cy123)
    >>> py123
    [1, 2, 3]
    >>> type(py123)
    <type 'list'>

You may also instruct ``curry.eval`` to convert results as they are
generated:

    >>> append = getattr(Prelude, '++')
    >>> goal3 = curry.expr(append, [1], [2,3])
    >>> next(curry.eval(goal3, converter='topython'))
    [1, 2, 3]

.. _Python Tutorial: https://docs.python.org/3/tutorial/

