==========
Quickstart
==========

.. toctree::

For the impatient among us, this quickstart guide demonstrates the basic usage
of Sprite.  You will lean how to install Sprite; run Curry programs from the
command line; and load modules, build expressions, and evaluate code from the
Python API.

Quick Build
===========

Ensure Python, PAKCS, and icurry are in your PATH, and that you are using
:ref:`compatible <Introduction/ExternalSoftware:Compatibility Software>`
versions.  Then configure and stage Sprite:

.. code-block:: bash

    ./configure
    make stage

.. note::

    Add ``$ROOT/install/bin`` to your PATH or supply full paths in the commands
    below.  $ROOT refers the Sprite repository root.

Running a Curry Program
=======================

Change the working directory to ``$ROOT/examples``, where you will find
a file named ``Peano.curry`` with the following contents:

.. code-block:: haskell

    data Nat = O | S Nat
    add :: Nat -> Nat -> Nat
    add O n = n
    add (S n) m = S (add n m)

    main :: Nat
    main = add (S O) (S O)

To compile and run this program, say:

.. code-block:: bash

    % sprite-exec Peano.curry
    S (S O)

The Python API
==============

Start Python by executing ``$ROOT/install/bin/python``.  This will
automatically set up your environment for Sprite.  To import Sprite, say:

    >>> import curry

Loading Curry Modules
---------------------

Curry modules can be imported into Python via the ``import`` keyword.  Any
import from the special module ``curry.lib`` will import Curry code.  We will
see an example of this shortly.

To import the ``Peano`` module, it is first necessary to set up the search path
for Curry files.  This resides in the list variable ``curry.path``.  Update
this variable to include the directory containing ``Peano.curry``.  If it is in
the current directory, for instance, you might say:

    >>> curry.path.insert(0, '.')

.. note::

  The initial value of ``curry.path`` comes by splitting the CURRYPATH environment
  variable on colons.

Now import ``Peano`` by saying:

    >>> from curry.lib import Peano

This compiles ``Peano`` and loads it into Python.  It can be examined or used to
build and evaluate expressions.

A reference to every loaded Curry module is stored in ``curry.modules``.  This
now contains the implict module ``Prelude`` as well as ``Peano``:

    >>> curry.modules
    {'Prelude': <curry module 'Prelude'>, 'Peano': <curry module 'Peano'>}


Inspecting Curry Code
---------------------

``Peano`` exposes its exported symbols through Python attributes.  Symbols are
constructor and function names.  These can be accessed in the usual way:

    >>> Peano.S
    <curry constructor 'Peano.S'>
    >>> Peano.O
    <curry constructor 'Peano.O'>
    >>> Peano.add
    <curry function 'Peano.add'>

Sprite also provides the function ``curry.symbol`` to look up any symbol by its
fully-qualified name:

    >>> curry.symbol('Peano.S')
    <curry constructor 'Peano.S'>

This function only searches loaded modules; it will not import anything.

To look up a type, use ``curry.type``:

    >>> curry.type('Peano.Nat')
    <curry type 'Peano.Nat'>

.. note::

    Types are not exposed as module attributes because they can conflict with
    symbol names.  To access types, use ``curry.type``, the ``curry.inspect``
    module, or access the "hidden" attribute ``.types`` as follows:

        >>> getattr(Peano, '.types')
        {'Nat': <curry type 'Peano.Nat'>}



These objects contain a wealth of information as you look deeper.  For examples:

    >>> Peano.add.name
    'add'
    >>> Peano.add.fullname
    'Peano.add'
    >>> Peano.add.info
    InfoTable(name='add', arity=2, tag=-1, _step=<not yet compiled>, format=None, typecheck=None, typedef=None, flags=0)

To see the ICurry and generated backend code try the following commands:

    >>> print Peano.add.icurry
    >>> print Peano.add.getimpl()


Dynamic Compilation
-------------------

Curry definitions can be created dynamically by using ``curry.compile``.  This
has the same effect as importing a Curry source file with the same contents.

For example:

    >>> Fib = curry.compile(
    ...   '''
    ...   fib :: Int -> Int
    ...   fib n | n < 3 = 1
    ...         | True  = (fib (n-1)) + (fib (n-2))
    ...   '''
    ... )


Building expressions
--------------------

To evaluate Curry code, one first builds an expression.  One way to do so is
with the function ``curry.expr``.  This function takes a mixed list of Curry
symbols or literals, and returns a Curry expression:

    >>> goal2 = curry.expr([Fib.fib, 7])
    >>> print goal2
    fib 7

This function automatically converts many Python objects into their Curry
equivalents.  Type ``help(curry.expr)`` at the Python prompt for details.

Nested expressions can be specified with nested lists:

    >>> print curry.expr([Peano.S, [Peano.S, Peano.O]])
    S (S O)

Expressions can also be created using ``curry.compile`` with the ``mode``
argument set to 'expr'.  This causes ``compile`` to interpret the Curry code as
an expression rather than a definition:

    >>> goal = curry.compile('add (S (S O)) (S O)', mode='expr', imports=[Peano])
    >>> print goal
    add (S (S O)) (S O)

Since the expression uses unqualified names, the Peano module needs to be
listed as an import to make its symbols visible.

Curry expressions have so far been printed as strings.  Applying ``repr``
produces a more direct visualization of the structure:

    >>> print repr(goal2)
    <fib <Int 7>>

Each bracketed expression describes a node, and consists of a label followed by
data arguments.  The data may include references to other nodes (which are
expanded) or unboxed fundamental values, such as integers, floating-point
numbers, or characters.  The number appearing in the above expression consists
of a Curry node of type ``Int`` holding an unboxed value, ``7``, in its data
section.  Using this format, there are no special rules for formatting lists,
tuples, or strings.


Evaluating expressions
----------------------

To evaluate an expression pass it to ``curry.eval``.

    >>> print next(curry.eval(goal))
    S (S (S O))
    >>> print next(curry.eval(goal2))
    13

``curry.eval`` returns a generator that yields one value of the goal with each
invocation of ``next``.  The goal is evaluated lazily, meaning that each call
to ``next`` performs the minimum evaluation necessary to compute the next
value.

