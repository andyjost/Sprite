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

Sprite runs the goal ``main`` by default, or you can use ``-g`` to specify a
different one.

The Python API
==============

Start Python by executing ``$ROOT/install/bin/python``.  To import Sprite, say:

    >>> import curry

At this point, you may wish to use ``dir`` and ``help`` to explore for
yourself.  To list the functions, submoudles, and other objects provided by
Sprite, say:

    >>> dir(curry)

To read the help documentation, pass any of these objects to the ``help``
command.  Take this opportunity to say:

    >>> help(curry)


Loading Curry Modules
---------------------

Curry modules can be imported into Python via the ``import`` keyword.  To avoid
ambiguity with Python modules, Curry code is imported from a virtual package called
``curry.lib``.  We will see an example shortly.

To import ``Peano`` it is first necessary to configure the search path residing
at ``curry.path``.  To prepend the current directory, say:

    >>> curry.path.insert(0, '.')

.. note::

  The initial value of ``curry.path`` comes from the environment variable
  CURRYPATH.

Now, to compile ``Peano`` and load it into Python, say:

    >>> from curry.lib import Peano

The module can now be examined or used to build and evaluate expressions.

Whenever a Curry module is imported, a reference to it is stored in
``curry.modules``.  We can see that it now contains the implict module
``Prelude`` as well as ``Peano``:

    >>> curry.modules
    {'Prelude': <curry module 'Prelude'>, 'Peano': <curry module 'Peano'>}


Inspecting Curry Code
---------------------

Inspecting Symbols
..................

``Peano`` has an attribute for each public symbol (i.e., constructor or
function) in the Curry source.  These can be accessed in the usual way:

    >>> Peano.S
    <curry constructor 'Peano.S'>
    >>> Peano.O
    <curry constructor 'Peano.O'>
    >>> Peano.add
    <curry function 'Peano.add'>

These objects contain a wealth of information.

.. tip::
   Rely on the ``dir`` function rather than documentation to more fully explore these.

For example:

    >>> Peano.add.name
    'add'
    >>> Peano.add.fullname
    'Peano.add'
    >>> Peano.add.info
    InfoTable(name='add', arity=2, tag=-1, _step=<not yet compiled>, format=None, typecheck=None, typedef=None, flags=0)

To see the ICurry and generated backend code try the following commands:

    >>> print(Peano.add.icurry)
    >>> print(Peano.add.getimpl())

Sprite provides the function ``curry.symbol``, which can find a symbol
by its fully-qualified name:

    >>> curry.symbol('Peano.S')
    <curry constructor 'Peano.S'>

This function only searches loaded modules; it will not import anything.

Inspecting Types
................

Sprite provides the function ``curry.type``, which can find a type by its
fully-qualified name:

    >>> Nat = curry.type('Peano.Nat')
    >>> Nat
    <curry type 'Peano.Nat'>

.. note::

    Types are not exposed as module attributes because they can conflict with
    symbol names.

Type objects contain useful information:

    >>> Nat.module()
    <curry module 'Peano'>
    >>> Nat.constructors
    [<curry constructor 'Peano.O'>, <curry constructor 'Peano.S'>]


Dynamic Compilation
-------------------

Curry definitions can be created on the fly with ``curry.compile``:

    >>> Fib = curry.compile(
    ...     '''
    ...     fib :: Int -> Int
    ...     fib n | n < 3 = 1
    ...           | True  = (fib (n-1)) + (fib (n-2))
    ...     '''
    ...   , modulename='Fib'
    ...   )


.. note::

    Sprite dedents leading whitespace common to every line, so Curry code can
    be formatted in blocks, as shown above.

This by default interprets the string as a module definition.  To build an
expression, set the mode to ``'expr'``:

    >>> fib3 = curry.compile('fib 3', mode='expr', imports=[Fib])

Adding ``Fib`` to the import list makes ``Fib.fib`` available.

Building Expressions in Python
------------------------------

Curry expressions can be created directly in Python with ``curry.expr``.  One
might use this to improve performance, as it bypasses the Curry fronend.  This
approach, however, performs neither type deduction or validation.

.. warning::

   Use extreme caution when building complex expressions with ``curry.expr`` so
   as not to introduce type errors.

``curry.expr`` takes a mixed list of Curry symbols and literals.  It returns a
``CurrExpression`` object:

    >>> fib7 = curry.expr([Fib.fib, 7])
    >>> print(repr(fib7))
    <curry function expression: head='fib'>
    >>> print(fib7)
    fib 7

This function automatically converts many Python objects into their Curry
equivalents.  Type ``help(curry.expr)`` at the Python prompt for details.

Nested expressions can be specified with nested lists:

    >>> print(curry.expr([Peano.S, [Peano.S, Peano.O]]))
    S (S O)

Curry expressions have so far been printed as strings.  Applying ``repr``
produces a more direct visualization of the structure:

    >>> print(repr(fib7))
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

    >>> print(next(curry.eval(goal)))
    S (S (S O))
    >>> print(next(curry.eval(fib7)))
    13

``curry.eval`` returns a generator that yields one value with each invocation
of ``next``.  The goal is evaluated lazily, so ``next`` performs only the
computational steps it must to compute the next value.

By default, no conversions are performed.  That means the '13' returned above is a
Curry integer rather than a Python integer.  We can see this by looking at the type:

    >>> value = next(curry.eval(fib7))
    >>> print(type(value))


.. warning::
    Gotta say something about type annotations.


Non-deterministic computations are in general multi-valued.  To
partially evaluate an expression, simply drop the generator.  To print
the Fibonacci numbers less than 100, for instance, your could say:

    >>> fibs = curry.compile(
    ...     'anyOf (map fib [1..])', mode='expr', exprtype='Int', imports=[Fib]
    ...   )
    >>> for value in curry.eval(fibs, converter='topython'):
    ...   if value < 100:
    ...     print(x)
    ...   else:
    ...     break
    1
    1
    2
    3
    5
    8
    13
    21
    34
    55
    89

Converting Values
-----------------
 The previous examplek
