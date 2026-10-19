==========
Quickstart
==========

After :doc:`Installation/Installation`, spend five minutes with lessons 01 and
02.  From the repository root, run ``make stage`` and put ``install/bin``
on ``PATH``.  ``python -m curry`` or ``sprite-exec`` without a program
starts the :doc:`Curry REPL <REPL>`; with a filename, either runs that
program.  Start Python from ``examples/`` for the Python API examples
below.  For the rest of the tour, continue with :doc:`PythonAPI/UsingTheAPI`;
:doc:`Examples` is the catalogue.

1. Hello, both ways
===================

The first lesson's small module accepts a Python value and returns one:

    >>> import curry
    >>> curry.path.insert(0, '01-run-with-python')
    >>> from curry.lib import Hello
    >>> curry.eval(Hello.greet('Python')).one()
    'Hello, Python!'

Run ``./run`` in ``examples/01-run-with-python`` for the complete
:ref:`lesson <example-01>`, including several answers and three corrected
mistakes.  The guide explains :ref:`results-lifecycle` and
:ref:`values-and-types` when you are ready for them.

2. Compile and parse
====================

The second lesson builds a small module from source text, then builds a
text goal with that module in scope:

    >>> Nat = curry.compile('''
    ... data Nat = O | I Nat deriving Show
    ... natToInt :: Nat -> Int
    ... natToInt O = 0
    ... natToInt (I n) = 1 + natToInt n
    ... ''')
    >>> goal = Nat.natToInt(Nat.I(Nat.O))
    >>> curry.eval(goal).one()
    1
    >>> goal = curry.parse('natToInt (I (I O))', imports=[Nat])
    >>> curry.eval(goal).one()
    2

Run ``./run`` in ``examples/02-dynamic-code-generation`` for the complete
:ref:`lesson <example-02>`.  Continue with the guide's
:ref:`tree values <values-and-match>`, :ref:`logic <logic-choices>` and
:ref:`encapsulated search <set-functions>`.  For command-line execution,
start with :ref:`00 <example-00>`; for an interactive session, see
:doc:`REPL`.
