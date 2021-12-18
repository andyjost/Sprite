=============
Using the API
=============

.. note::

    To try the examples in this file, start an interactive Python
    prompt.  See :ref:`starting-python` for details.

Importing Curry Modules
=======================

Curry modules can be imported into Python via the ``import`` keyword.  To avoid
ambiguity with Python modules, Curry code is imported from a virtual package called
``curry.lib``.  We will see an example shortly.

To import ``Peano`` it is first necessary to configure the search path residing
at ``curry.path``.  The initial value of this comes from the environment
variable CURRYPATH.  If your CURRYPATH does not already contain the current
directory, you can add it by saying:

    >>> curry.path.insert(0, '.')

Now, import ``Peano``:

    >>> from curry.lib import Peano

This compiles the code of ``Peano`` into executable form, loads it into a
Python module, and registers that object with Python.

Whenever a Curry module is imported, a reference to it is stored in
``curry.modules``.  We can see that it now contains the implict module
``Prelude`` as well as ``Peano``:

    >>> curry.modules
    {'Prelude': <curry module 'Prelude'>, 'Peano': <curry module 'Peano'>}

Inspecting Symbols
==================

``Peano`` exposes public symbols (i.e., constructors and functions) as Python
attributes.  These can be accessed in the usual way:

    >>> Peano.S
    <curry constructor 'Peano.S'>
    >>> Peano.O
    <curry constructor 'Peano.O'>
    >>> Peano.add
    <curry function 'Peano.add'>

These objects contain a wealth of information.  For example:

    >>> Peano.add.name
    'add'
    >>> Peano.add.fullname
    'Peano.add'
    >>> Peano.add.info
    InfoTable(name='add', arity=2, tag=-1, _step=<not yet compiled>, format=None, typecheck=None, typedef=None, flags=0)

To see the ICurry and generated backend code try the following commands:

    >>> print(Peano.add.icurry)
    >>> print(Peano.add.getimpl())

.. tip::
    Use ``print`` when examining long strings with embedded newlines.

Sprite provides the function ``curry.symbol`` to find symbols by their
fully-qualified name:

    >>> curry.symbol('Peano.S')
    <curry constructor 'Peano.S'>

This function only searches loaded modules; it will not import anything.

Inspecting Types
================

Curry types and symbols reside in separate namespaces.  To avoid
collisions, types are not exposed as module attributes in Python.

Sprite provides ``curry.inspect.types`` to gain access to the types defined in
a module:

    >>> from curry import inspect
    >>> inspect.types(Peano)
    {'Nat': <curry type 'Peano.Nat'>}

One may also use ``curry.type`` to look up a type by its fully-qualified name:

    >>> curry.type('Peano.Nat')
    <curry type 'Peano.Nat'>

Type objects possess several attributes worth exploring:

    >>> Nat = curry.type('Peano.Nat')
    >>> Nat.module()
    <curry module 'Peano'>
    >>> Nat.constructors
    [<curry constructor 'Peano.O'>, <curry constructor 'Peano.S'>]


Compiling Curry Code
====================

Dynamic Compilation
-------------------

Use :func:`curry.compile`` to dynamically create Curry modules:

    >>> Fib = curry.compile(
    ...     '''
    ...     fib :: Int -> Int
    ...     fib n | n < 3 = 1
    ...           | True  = (fib (n-1)) + (fib (n-2))
    ...
    ...     main :: Int
    ...     main = fib 7
    ...     '''
    ...   , modulename='Fib'
    ...   )
  
The above is equivalent to to placing the code into a file ``Fib.curry`` and
importing it.  If a module name is provided, the module is added to
:data:`curry.modules`.

.. note::

    Sprite dedents leading whitespace common to every line, so Curry code can
    be formatted in blocks, as shown above.

Writing Compiled Code to Disk
-----------------------------

Use :func:`curry.save` to write out compiled Curry.  For example, to save the
compiled Fib module into a file ``Fib.py``, say:

    >>> curry.save(Fib, 'Fib.py')

This can be loaded in another session with :func:`curry.load`:

    >>> Fib = curry.load('Fib.py')

.. note::

    Attempting to load ``Fib.py`` in the same session ``Fib`` was defined will
    result in an error saying the module is already defined.  There are a few
    ways around this:

        1. Say ``del curry.modules['Fib']`` to remove the existing module.
        2. Say ``curry.reset()`` to reset the global interpreter.
        3. Load the module into a new interpreter:

               >>> from curry.interpreter import Interpreter
               >>> interp = Interpreter()
               >>> interp.load('Fib.py')

Building Expressions
====================

The string to ``curry.compile`` is by default interpreted as a module
definition.  To instead build an expression, set the mode to ``'expr'``:

    >>> fib3 = curry.compile(
    ...     'fib 3', mode='expr', exprtype='Int', imports=[Fib]
    ...   )

Note the following:

    - ``exprtype`` provides the type annotation of this expression.  See
      :ref:`important-notes`.
    - Adding ``Fib`` to the import list makes ``Fib.fib`` available.

Simple Curry expressions can also be created directly in Python with
``curry.expr``.  One might use this to improve performance, as it bypasses the
Curry frontend.  Beware, however, that this approach performs neither type
deduction or type validation.

.. warning::

   Use caution when building complex expressions with ``curry.expr``.
   Evaluating an expression with type errors will result in undefined behavior.

Built-in Conversions
....................

``curry.expr`` converts numbers, strings, Booleans, lists, and tuples to Curry.
A few examples:

    >>> curry.expr(1)
    <Int 1>
    >>> curry.expr('a')
    <Char 'a'>
    >>> curry.expr(True)
    <True>
    >>> curry.expr([1])
    <: <Int 1> <[]>>
    >>> curry.expr((1,2))
    <(,) <Int 1> <Int 2>>

The above values are shown in ``repr`` format.  This format can be obtained by
applying the ``repr`` function.  This format reflects the underlying graph
structure directly.  Each node is rendered as an angle-bracket-enclosed
sequence comprising the symbol name followed by the successors.  No special
formatting for lists, tuples, strings, or any other type is used.

Boxed values, such as ``<Int 1>``, are easy to distinguish from unboxed ones.
To be boxed is synonymous with being stored in a node.  The boxed integer
``<Int 1>`` is a node with symbol ``Int`` and successor ``1`` (which is
unboxed).  To specify unboxed data, wrap it with ``curry.unboxed``:

    >>> curry.expr(curry.unboxed(1))
    1

An alternative to ``repr`` format is ``str`` format.  To obtain it,
apply the ``str`` function or just print the value:

    >>> print(curry.expr(1))
    1
    >>> print(curry.expr('a'))
    'a'
    >>> print(curry.expr('hello'))
    "hello"
    >>> print(curry.expr([1]))
    [1]
    >>> print(curry.expr((1,2)))
    (1, 2)

``str`` format shows expressions in a more natural way, but discards
information about whether data is boxed.

Symbolic Expressions
....................

Curry symbols are converted to expressions:

    >>> from curry.lib import Prelude
    >>> curry.expr(Prelude.Nothing)
    <Nothing>

To apply arguments, place them after the symbol:

    >>> curry.expr(Prelude.Just, 5)
    <Just <Int 5>>
    >>> curry.expr(Fib.fib, 7)
    <fib <Int 7>>

Partial applications are allowed:

    >>> curry.expr(Prelude.Just)
    <_PartApplic 1 <Just>>

A subexpression can be specified as a Python list whose first element is a
symbol:

    >>> print(curry.expr(Peano.S, [Peano.S, Peano.O]))
    S (S O)

.. note::

  Using Python lists to build both Curry lists and nested Curry expressions may
  seem to introduce an ambiguity.  This is not the case, though the reason is
  subtle.  Lists are processed recursively from the inside out and treated as
  subexpressions only when their first element is strictly a  *symbol*.
  Consider:

      >>> print(curry.expr([Peano.S, Peano.O]))
      S O

  This list specifies a subexpression because ``Peano.S`` is a symbol.  On the
  other hand:

      >>> print(curry.expr([[Peano.O], [Peano.O]]))
      [O, O]

  The nested lists, ``[Peano.O]``, begin with a symbol and, therefore, specify
  subexpressions.  These are transformed first by applying ``curry.expr``
  recursively.  By the time it is processed, the outermost list begins with an
  expression rather than a symbol.

Graph-Like Expressions
......................

Named subexpressions can be created by passing keyword arguments.  This is
necessary to create graph-like (as opposed to tree-like) expressions that
contain shared subexpressions and/or cycles.  To reference a subexpression, use
``curry.ref``.  The following creates an infinity in the Peano system:

    >>> curry.expr(curry.ref('a'), a=[Peano.S, curry.ref('a')])
    <S ...>

This is equivalent to the following Curry expression:

.. code-block:: haskell

    let a=(S a) in a

The ellipsis indicates a back reference.  In general, ``repr`` will not render
a subexpression more than once.  ``str`` format does not do this, so an attempt
to print the previous expression would never terminate.

Expression Modifiers
....................

In addition to ``curry.ref``, a few other helper functions and objects are
provided.  To create a free variable, use ``curry.free``:

    >>> print(curry.expr(curry.free()))
    _0

To create a non-deterministic choice, use ``curry.choice``:

    >>> curry.expr(curry.choice(1, 2))
    <Choice 0 <Int 1> <Int 2>

The number immediately following ``Choice`` is the choice identifier.  This can
be specified by providing three arguments to ``curry.choice``, or you can let
the ``curry.expr`` assigned it for you.

Use ``curry.cons`` and ``curry.nil`` to create cons-style lists:

    >>> print(curry.expr(curry.cons(1, curry.nil)))
    [1]


Evaluating Expressions
======================

To evaluate an expression pass it to ``curry.eval``.

    >>> print(next(curry.eval(goal)))
    S (S (S O))
    >>> print(next(curry.eval(fib7)))
    13

``curry.eval`` returns a generator that yields one value with each invocation
of ``next``.  The goal is evaluated lazily, so ``next`` performs only the
computational steps it must to compute the next value.

By default, no conversions are performed.  That means the ``13`` returned above
is a Curry integer rather than a Python integer.  We can see this by looking at
the ``repr`` format:

    >>> next(curry.eval(fib7))
    <Int 13>

Multi-Valued Computations
-------------------------

Non-deterministic computations are in general multi-valued.  To partially
evaluate such an expression, simply stop taking values and discard the
generator.  For example, to print the Fibonacci numbers less than 30 one could
say:

    >>> fibs = curry.compile(
    ...     'anyOf (map fib [1..])', mode='expr', exprtype='Int', imports=[Fib]
    ...   )
    >>> for value in curry.eval(fibs, converter='topython'):
    ...   if value < 30:
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

Conversions to Python
=====================

:func:`curry.expr` provides conversions from Python to Curry.  The reverse can
be performed with :func:`curry.topython`.  This function recursively converts a
Curry expression to Python.

Conversions to the following Python types are performed: ``bool``, ``float``,
``int``, ``list``, ``str``, ``tuple``.

:func:`curry.topython` prunes the recursion wherever it encounters a
subexpression it cannot convert.  The reason for this potentially
counter-intuitive behavior is made clear by the following example:

    >>> just5 = curry.expr(Prelude.Just, 5)
    >>> curry.topython(just5)
    >>> <Just <Int 1>>

One might expect the boxed integer to be converted to a Python integer, but
that would lead to an ill-typed expression.  Sprite leaves it to the user to
avoid this or convert such values another way.

