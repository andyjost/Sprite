===========
Interaction
===========

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


Building Expressions
====================

The string to ``curry.compile`` is by default interpreted as a module
definition.  To instead treat it as an expression, set the mode to ``'expr'``:

    >>> fib3 = curry.compile('fib 3', mode='expr', imports=[Fib])

Adding ``Fib`` to the import list makes ``Fib.fib`` available.

Simple Curry expressions can also be created directly in Python with
``curry.expr``.  One might use this to improve performance, as it bypasses the
Curry frontend.  Beware, however, that this approach performs neither type
deduction or type validation.

.. warning::

   Use caution when building complex expressions with ``curry.expr``.
   Evaluating an expression with type errors will result in undefined behavior.

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

Use ``print`` to render Curry expressions in a more natural form:

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

Curry symbols are converted to expressions:

    >>> from curry.lib import Prelude
    >>> curry.expr(Prelude.Nothing)
    <Nothing>

To apply arguments, place them after the symbol:

    >>> curry.expr(Prelude.Just, 5)
    <Just <Int 5>>
    >>> curry.expr(Fib.fib, 7)
    <fib <Int 7>>

Subexpressions can be created by passing  Python list:

    >>> print(curry.expr(Peano.S, [Peano.S, Peano.O]))
    S (S O)

Named subexpressions can be created by passing keyword arguments.  This is
necessary to create graph-like (as opposed to tree-like) expressions that
contain shared subexpressions and/or cycles.  To reference a subexpression, use
``curry.ref``.  The following creates an infinity in the Peano system:

    >>> curry.expr(ref('a'), a=[Peano.S, curry.ref('a')])
    <S ...>

The ellipsis indicates a back reference.  The above is equivalent to the following
Curry expression::

.. code-block: haskell

    let a=(S a) in a

In addition to ``curry.ref``, a few other helper functions and objects are
provided.  To create a free variable, use ``curry.free``:

    >>> print(curry.expr(curry.free()))
    _0

To create a non-deterministic choice, use ``curry.choice``:

    >>> curry.expr(curry.choice(1, 2))
    <Choice 0 <Int 1> <Int 2>

Use ``curry.cons`` and ``curry.nil`` to create cons-style lists:

    >>> print(curry.expr(curry.cons(1, curry.nil)))
    [1]


..
    Without ambiguity, nested expressions can be specified with nested lists:


    This
    By comparison, a list containing two ``Peano.O`` objects is written:

        >>> print(curry.expr([[Peano.O], [Peano.O]])
        [O, O]

    Note that in the context of ``curry.expr``, ``Peano.O`` is a symbol whereas
    ``[Peano.O]`` is an expression.

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


Evaluating Curry Code
=====================

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

Interoperability
================


