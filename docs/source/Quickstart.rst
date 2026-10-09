==========
Quickstart
==========

.. toctree::

For the impatient among us, this guide demonstrates some basic capabilities of
Sprite.  It shows how to install Sprite, run Curry programs from the command
line, and load modules, build expressions, evaluate code, and convert values
using the Python API.

.. important::

    To run the examples, prepend ``install/bin`` to your PATH or use
    fully-qualified names.

Quick Install
=============

* For the bold:

    .. code-block:: bash

        wget -qO- https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh

    See :ref:`easy-install` for more options.

* For the cautious:

    .. code-block:: bash

        git clone https://github.com/andyjost/Sprite.git
        cd Sprite
        ./configure --check-prereqs

    If you are satisfied with how the prerequisites will be installed:

    .. code-block:: bash

        ./configure --install-prereqs --yes
        make

    See :ref:`custom-install` for more options.


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

To evaluate this program, run ``sprite-exec`` from the ``examples/``
directory.  If ``install/bin`` is not on your PATH, give the relative path:

.. code-block:: bash

    % ../install/bin/sprite-exec Peano.curry
    S (S O)

Sprite runs goal ``main`` by default.  You can use ``-g`` to specify a
different one.

The C++ backend runs a module interpreted until the compiled code is
ready, so an installation without a C++ compiler runs every program (see
:doc:`Installation/WithoutCompiler`).

The other subdirectories of ``examples/`` hold larger examples.  Each has a
run script, a README, and its expected output.  See :doc:`Examples`.

Python API Quickstart
=====================

The Python API is where the imperative, functional, and logic paradigms are
integrated.  It provides the 'glue' with which one creates, compiles, saves,
loads, and executes Curry code.

To begin, start Python:

.. code-block:: bash

    % install/bin/python

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
    <curry constructor 'S'>
    >>> Peano.add
    <curry function 'add'>

Not all Curry symbols are valid Python identifiers.  Use ``getattr`` to access
these:

    >>> getattr(Prelude, '++')
    <curry function '++'>

You may also find symbols by their full names using :func:`curry.symbol`:

    >>> curry.symbol('Prelude.++')
    <curry function '++'>


Building and Evaluating Goals
-----------------------------

To build a goal, use :func:`curry.compile` with mode ``'expr'``:

    >>> goal = curry.compile(
    ...     'add (S O) (S O)', mode='expr', exprtype='Nat', imports=[Peano]
    ...   )

``exprtype`` names the type of the expression.  Without it, the front end
infers the type, and class constraints are defaulted as the REPL of PAKCS
does: ``curry.compile('1 + 2', mode='expr')`` evaluates to the ``Int``
``3``.

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

:func:`curry.expr` types the expression before it builds it.  It reads the
type of each symbol from the interface the front end wrote, converts each
Python value by the type its position expects, and supplies the class
dictionaries of overloaded functions.  So a class method can be called from
Python, and a type error is reported when the expression is built, not
when it is evaluated:

    >>> plus = curry.symbol('Prelude.+')
    >>> print(next(curry.eval(plus, 1, 2)))
    3
    >>> curry.typeof(curry.expr(plus, 1, 2))
    'Num a => a'
    >>> curry.expr(getattr(Prelude, 'not'), 1)
    Traceback (most recent call last):
      ...
    curry.typecheck.errors.ConversionError: cannot convert 1 to Bool at argument 1 of Prelude.not :: Bool -> Bool

See :ref:`typed-expressions` for the conversion rules.  The untyped builder
:func:`curry.raw_expr` remains for the runtime and its tests; evaluating an
ill-typed expression built with it results in undefined behavior.

To build an expression containing a choice, use ``Prelude.?``:

    >>> print(curry.expr(getattr(Prelude, '?'), 1, 2))
    (?) 1 2

To build an expression containing a free variable, use :class:`curry.free`.
One marker is one variable: the expression holds a call of
``Prelude.unknown``, and the first rewrite step turns it into the variable.

    >>> xs = curry.free()
    >>> print(curry.expr(xs))
    unknown _inst#Prelude.Data#Prelude.Bool
    >>> print(next(curry.eval(xs)))
    _a

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
    <class 'list'>

You may also instruct :func:`curry.eval` to convert results as they are
generated:

    >>> append = getattr(Prelude, '++')
    >>> goal3 = curry.expr(append, [1], [2,3])
    >>> next(curry.eval(goal3, converter='topython'))
    [1, 2, 3]

Saving Compiled Curry
---------------------

:func:`curry.save` writes the generated C++ of a module:

    >>> curry.save(Peano, 'Peano.cpp', module_main=False)

Use this to see how Sprite compiles Curry.  ``module_main=False`` saves
the module alone.  Without it the file is a program, and ``goal=`` must
name the goal it evaluates; a call with neither raises ``ValueError``.
The entry point of the C++ program is a stub today: ``sprite-exec`` runs
programs.

:func:`curry.load` loads the shared object of a module, which
``sprite-make --so`` writes beside the source (see :ref:`sprite-make`):

.. code-block:: bash

    % install/bin/sprite-make --so Peano.curry

Then, in Python:

    >>> Peano = curry.load('.curry/sprite-pakcs-3.4.1/Peano.so')

The call adds ``Peano`` to :data:`curry.modules`.  Under the default
setting of the C++ backend, ``interpret:tiered``, the import of ``Peano``
above already started a compile of the module in the background when no
current object existed; :func:`curry.load` of its object waits for that
compile to end and loads the object it wrote, so the sequence works while
the compile runs.  That compile writes the files ``sprite-make --so``
writes, so run ``sprite-make`` once the background compile ended (a few
seconds for a module of this size), not at the same time.  A module whose library is loaded already from another
file is refused: the runtime keeps one library per module name for the
life of the process.  An edit of ``Peano.curry`` after the import is not
read again in this process; a new process reads it.

.. _Python Tutorial: https://docs.python.org/3/tutorial/

