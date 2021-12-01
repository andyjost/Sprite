============================
Quickstart
============================

.. toctree::

This introduction shows how to interact with the Sprite Curry system via its
Python interface.  You will lean how to load Curry modules, build Curry
expressions, and evaluate code.

To get started, invoke the Python executable found at $PREFIX/bin/python.  This
will automatically set up the PYTHONPATH environment variable, making Sprite
available.

The Sprite Curry system is in the ``curry`` module.

  >>> import curry


Using Modules
=============

Curry modules can be loaded from files or defined dynamically.  This section
describes how to work with modules in Sprite.


Loading Curry modules
---------------------

Curry code can be imported into Python using the Python import mechanism.  Any
import from the special module ``curry.lib`` will import Curry code.  To try
this, place the following code into a file named ``Peano.curry``.

.. code-block:: haskell

    data Nat = O | S Nat
    add :: Nat -> Nat -> Nat
    add O n = n
    add (S n) m = S (add n m)

To import the ``Peano`` module, it is first necessary to set up the search path
for Curry files.  This resides in the list variable ``curry.path``.  Update this
variable to include the directory containing the file you just created.  If it
is in the current directory, you might say:

    >>> curry.path.insert(0, '.')

Now import the ``Peano`` module with the following statement:

    >>> from curry.lib import Peano

The initial value of ``curry.path`` comes by splitting the CURRYPATH environment
variable on colons.

Curry definitions can be created dynamically by using ``curry.compile``.  This
has the same effect as importing a Curry source file with the same contents.

Example:

    >>> Fib = curry.compile(
    ...   '''
    ...   fib :: Int -> Int
    ...   fib n | n < 3 = 1
    ...         | True  = (fib (n-1)) + (fib (n-2))
    ...   '''
    ... )


Building expressions
--------------------

A loaded Curry module provides a set of definitions.  These appear as
attributes.

    >>> Peano.S
    <curry constructor 'Peano.S'>
    >>> Peano.O
    <curry constructor 'Peano.O'>
    >>> Fib.fib
    <curry function '_interactive_.fib'>

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

