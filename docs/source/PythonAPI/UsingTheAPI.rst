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
    >>> Peano.add.signature
    'Nat -> Nat -> Nat'

The signature is the type scheme of the symbol in Curry syntax.  Sprite reads
it from the FlatCurry interface that the front end wrote beside the module.
``Peano.add.scheme`` is the same scheme as an object; see
:mod:`curry.typecheck`.  A symbol of the Prelude with a class constraint
shows its context:

    >>> curry.symbol('Prelude.+').signature
    'Num a => a -> a -> a'

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

    >>> curry.save(Fib, 'Fib.py', module_main=False)

``module_main=False`` saves the module alone.  Without it the file is a
program, and ``goal=`` must name the goal it evaluates.  This can be loaded
in another session with :func:`curry.load`:

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

.. _building-expressions:

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

``exprtype`` is optional.  Without it the front end infers the type of the
expression.  A type with class constraints, such as ``Num a => a`` for
``1 + 2``, is defaulted as the REPL of PAKCS does: ``Num`` to ``Int``,
``Fractional`` to ``Float``, ``Monad`` to ``IO``, a lone ``Data`` to
``Bool``.  A constraint the table cannot handle is a ``CompileError`` with
the sentence of the REPL.  A trailing ``where x, y free`` declares free
variables, as in the REPL.  A variable whose type is absent from the result
type cannot show in a value, so ``curry.eval`` reports its binding with each
value, as the REPL of PAKCS prints it:

    >>> goal = curry.compile('xs ++ [3] =:= [1, 2, 3] where xs free', mode='expr')
    >>> print(next(curry.eval(goal)))
    {xs=[1, 2]} True

A variable whose type occurs in the result type is left in the value, which
is the answer:

    >>> print(next(curry.eval(curry.compile('(x, 1) where x free', mode='expr'))))
    (_a, 1)

Curry expressions can also be created directly in Python with
:func:`curry.expr`.  It bypasses the Curry front end, so it is fast, and it
is typed: the expression is checked and converted before any node is built.
:ref:`typed-expressions` below gives the rules.

Built-in Conversions
--------------------

``curry.expr`` converts numbers, strings, Booleans, lists, and tuples to Curry,
each by the type its position expects (see :ref:`typed-expressions`).  A few
examples:

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
    >>> print(next(curry.eval('hello')))
    "hello"
    >>> print(curry.expr([1]))
    [1]
    >>> print(curry.expr((1,2)))
    (1, 2)

``str`` format shows expressions in a more natural way, but discards
information about whether data is boxed.  A string of several characters is
built in one call: on the Python backend as one ``_biString`` node, which
prints as ``_biString 'hello'`` until the first step unfolds it, and on the
C++ backend as the list of its characters, made natively.  Neither form is
bounded by the recursion limit.  The example above evaluates the string so
that both backends print the same text.

Symbolic Expressions
--------------------

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
----------------------

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
--------------------

In addition to ``curry.ref``, a few other helper functions and objects are
provided.  To create a free variable, use ``curry.free``.  One marker is one
variable, also when it occurs several times or in several expressions.  The
expression holds a call of ``Prelude.unknown``, and the first rewrite step
turns it into the variable.  ``curry.reset()`` starts a new interpreter
state, and the marker becomes a new variable there:

    >>> xs = curry.free()
    >>> print(curry.expr(xs))
    unknown _inst#Prelude.Data#Prelude.Bool
    >>> print(next(curry.eval(xs)))
    _a

To create a non-deterministic choice, use ``curry.choice``.  The expression
holds a call of ``Prelude.?``, and the first rewrite step turns it into a
choice with a fresh identifier:

    >>> print(curry.expr(curry.choice(1, 2)))
    (?) 1 2
    >>> sorted(curry.eval(curry.choice(1, 2), converter='topython'))
    [1, 2]

``curry.raw_expr`` builds the raw ``Free`` and ``Choice`` nodes instead, with
the identifiers given to the markers.  That form serves the tests of the
runtime.

Use ``curry.cons`` and ``curry.nil`` to create cons-style lists:

    >>> print(curry.expr(curry.cons(1, curry.nil)))
    [1]


.. _typed-expressions:

Typed Expressions
-----------------

:func:`curry.expr` types an expression before it builds it.  The type
scheme of each symbol comes from the FlatCurry interface of its module, the
``signature`` shown above.  The arguments are unified with the parameter
types.  The class constraints that remain are defaulted with the table of
the PAKCS REPL (``Num`` to ``Int``, ``Fractional`` to ``Float``, ``Monad``
to ``IO``, a lone ``Data`` to ``Bool``), and the class dictionaries are
supplied.  So an overloaded function, and a class method, can be called
from Python:

    >>> plus = curry.symbol('Prelude.+')
    >>> print(curry.expr(plus, 1, 2))
    apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2
    >>> next(curry.eval(plus, 1, 2, converter='topython'))
    3
    >>> next(curry.eval(plus, 1.5, 1, converter='topython'))
    2.5
    >>> next(curry.eval(Prelude.show, [Prelude.Just, 1], converter='topython'))
    'Just 1'

:func:`curry.typeof` gives the type of an expression, of a symbol, or of
any argument ``curry.expr`` accepts: the inferred scheme before defaulting,
which is what ``:type`` prints in the :ref:`REPL <repl>`, or the type after
it:

    >>> curry.typeof(curry.expr(plus, 1, 2))
    'Num a => a'
    >>> curry.typeof(curry.expr(plus, 1, 2), defaulted=True)
    'Int'
    >>> curry.typeof(plus)
    'Num a => a -> a -> a'
    >>> curry.typeof([1, 2.5])
    'Fractional a => [a]'
    >>> curry.typeof((1, 2.5))
    '(Num a, Fractional b) => (a, b)'

The context is printed in the order of the front end: by the first type
variable of each constraint, then by the class.

The keyword ``exprtype`` states the type of the whole expression in Curry
syntax, and :class:`curry.typed` states the type of one part.  Both are
unified with the inferred type:

    >>> curry.typeof(curry.expr(Prelude.Just, 5, exprtype='Maybe Float'))
    'Maybe Float'
    >>> next(curry.eval(Prelude.read, '5', exprtype='Int', converter='topython'))
    5
    >>> curry.typeof(curry.typed(1, 'Float'))
    'Float'

**Conversion rules.**  A Python value converts by the type its position
expects.  The Python type decides only where the expected type is a type
variable.

* ``bool`` converts to ``True`` or ``False``.  Any other value under
  ``Bool`` is an error, so ``curry.expr(getattr(Prelude, 'not'), 1)`` is
  rejected.
* ``int`` converts to ``Int``; under ``Float`` to a ``Float``; under
  another instance of ``Num`` through ``fromInt``.  Under a type variable
  the variable gets the constraint ``Num`` and defaults to ``Int``.
* ``float`` converts to ``Float``; under a type variable the variable gets
  the constraint ``Fractional``.  A ``float`` under ``Int`` is an error, as
  ``1.5 + (1 :: Int)`` is in Curry.
* ``str`` converts to one string of any length under ``String``
  (``[Char]``): ``'a'`` under ``String`` is ``"a"``, and ``''`` is the
  empty string.  Under ``Char`` a ``str`` of length one converts to the
  character.  Under a bare type variable the Python type decides: a ``str``
  of length one is a ``Char``, and any other ``str`` is a ``String``;
  ``curry.typed('a', 'String')`` makes the one-character string.  The
  decision waits for the rest of the expression: another part that fixes
  the variable to a list makes the one-character string a string too, so
  ``['c', 'ab']`` is ``[String]`` in either order, and a type that only a
  list can fill, such as the ``f a`` of ``fmap``, makes it a string as
  well (``fmap ord 'a'`` is ``[97]``).  ``bytes`` convert as ``str``.
* ``list`` converts to a Curry list.  Every element takes the element
  type, and all elements unify before defaulting, so ``[1, 2.5]`` is
  ``[Float]``, as in Curry.  A list is built in a loop, so the builder puts
  no limit on its length.
* ``tuple`` converts to a Curry tuple; ``()`` is the unit.  Curry has no
  1-tuple, so a 1-tuple is an error.
* An iterator converts to a lazy Curry list.  The element type is fixed
  when the expression is built, by the context, by the other arguments or
  by the defaulting table, never by an item.  So a class constraint that
  only the items could resolve, as in ``map show`` over an iterator of
  numbers, is an error; ``curry.typed(iterator, '[Int]')`` states the
  element type.  An item that does not convert raises an
  ``EvaluationError`` when it is demanded, which ends the evaluation,
  inside ``?`` and inside a set function alike.
* ``None`` is an error that names the expected type.  Under ``Maybe t``
  the message suggests ``Prelude.Nothing``.
* A Curry node is typed by its content; see below.
* :class:`curry.free` is a free variable; see below.
* :class:`curry.unboxed` is the unboxed payload of an ``Int``, ``Char``
  or ``Float``.

**Values of earlier evaluations.**  A Curry node that fills a parameter is
typed by a walk of its content, to the leaves, not by its root alone.  The
values :func:`curry.eval` yields are copies of the result, so this walk is
what keeps a list of floats away from integer arithmetic:

    >>> v = next(curry.eval(curry.expr([1.5, 2.5])))
    >>> curry.typeof(v)
    '[Float]'
    >>> DL = curry.import_('Data.List')
    >>> next(curry.eval(DL.sum, v, converter='topython'))
    4.0

A partial application is typed by the scheme of its head and the arguments
it holds, so ``map not`` from an earlier evaluation has the type ``[Bool]
-> [Bool]`` and ``apply`` refuses a number for it.  The walk stops at
100000 nodes with an error, and refuses a value whose type would print
with more than that many nodes (a value that shares one node between the
components of a pair at every level has such a type).  State the type of
a larger value with ``curry.typed(node, '[Float]')``, which skips the
walk.  A node alone, or at the root of the expression, passes through
untouched.

**The scope of inference.**  One call of ``curry.expr`` is one inference
scope.  The class constraints of the call are defaulted when it returns,
and a later call does not reopen them:

    >>> incr = curry.expr(plus, 1)
    >>> curry.typeof(incr, defaulted=True)
    'Int -> Int'
    >>> curry.expr(Prelude.apply, incr, 1.5)
    Traceback (most recent call last):
      ...
    curry.typecheck.errors.ConversionError: cannot convert 1.5 to Int at argument 2 of Prelude.apply :: (a -> b) -> a -> b

To let the outer context decide, build the expression in one call, or
build a description with :func:`curry.describe`, which is typed with the
expression that receives it:

    >>> next(curry.eval(Prelude.apply, [plus, 1], 1.5, converter='topython'))
    2.5
    >>> d = curry.describe(plus, 1)
    >>> next(curry.eval(Prelude.apply, d, 1.5, converter='topython'))
    2.5

A description keeps the keyword anchors of its arguments and the keyword
``exprtype``; every use of it is typed afresh, so one description serves
several contexts.  A symbol without a type scheme (a module without a
FlatCurry interface, or a built-in of Sprite's own Prelude) is built
untyped when it stands alone, as the goal of a saved module is;
:func:`curry.typeof` refuses it, and an application of it is an error
that names ``raw_expr``.

**Free variables.**  A :class:`curry.free` marker is one variable, as
described above.  Its type comes from the context.  The marker carries no
constraint of its own, so ``curry.eval(Prelude.id, x)`` gives ``_a`` with
the type ``a``.  A consumer that needs ``Data``, such as ``=:=``, adds the
constraint, and a lone ``Data`` constraint defaults to ``Bool``, as in
PAKCS:

    >>> x, y = curry.free(), curry.free()
    >>> eq = getattr(Prelude, '=:=')
    >>> curry.typeof(curry.expr(eq, x, y))
    'Data a => Bool'
    >>> print(next(curry.eval(eq, x, y)))
    True

``curry.free(exprtype='[Int]')`` fixes the type of a variable.  A free
variable at a function type is an error at construction, because a free
variable of Curry must have a ``Data`` type.

Arithmetic on a free numeric variable does not narrow the variable.  A
free variable of a built-in type that reaches a case suspends the
evaluation, on both backends (issue #37), and the typed builder does not
change that: ``x + 1 =:= 3`` suspends, while ``x =:= 3`` binds ``x``, and a
conjunction in which another constraint binds ``x`` succeeds in either
order:

    >>> x = curry.free()
    >>> next(curry.eval(eq, [plus, x, 1], 3))
    Traceback (most recent call last):
      ...
    curry.exceptions.EvaluationSuspended: Evaluation Suspended!
    >>> y = curry.free()
    >>> conj = getattr(Prelude, '&')
    >>> print(next(curry.eval(conj, [eq, y, 3], [eq, [plus, y, 1], 4])))
    True

**Errors.**  A typing failure raises :class:`CurryTypeError
<curry.exceptions.CurryTypeError>` at construction; nothing is evaluated.
The message names the symbol with its scheme, the argument, and the types:

    >>> curry.expr(plus, 1, 'a')
    Traceback (most recent call last):
      ...
    curry.typecheck.errors.MismatchError: type mismatch in argument 2 of Prelude.+ :: Num a => a -> a -> a
      argument 1 fixed a := Int (from 1)
      argument 2 has type Char (from 'a')
    >>> curry.expr(Prelude.Just, 1, 2)
    Traceback (most recent call last):
      ...
    curry.typecheck.errors.ArityError: Prelude.Just :: a -> Maybe a takes 1 argument, 2 given

A class constraint that the table cannot default is an error with the
sentence of the PAKCS REPL; ``exprtype`` resolves it:

    >>> curry.expr(Prelude.read, '5')
    Traceback (most recent call last):
      ...
    curry.typecheck.defaulting.DefaultingError: cannot handle the overloaded expression 'read "5"' of type Read a => a
      Cannot handle arbitrary overloaded top-level expressions
      add a type annotation (exprtype)

**The untyped builder.**  :func:`curry.raw_expr` builds an expression
without types.  It converts every Python value by its Python type, checks
only the arity of a symbol, supplies no dictionary, and builds the raw
``Free`` and ``Choice`` nodes with the identifiers of the markers.  It
serves the runtime and its tests.

.. warning::

   :func:`curry.raw_expr` can produce an ill-typed expression.  Evaluating
   an ill-typed expression results in undefined behavior.

The interpreter flag ``typed_expr`` (``True`` by default) turns the typing
of :func:`curry.expr` off for a whole interpreter; see
:mod:`curry.interpreter.flags`.


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

A function of a module without a type signature keeps its class
constraints, which the front end turns into leading dictionary parameters.
``curry.eval`` supplies the dictionaries after the defaulting described
above, so ``main = Just 5`` evaluates to ``Just 5`` and not to a partial
application.  A call with arguments, ``curry.eval(M.addOne, 1)``, is typed
like any expression of :func:`curry.expr`.

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

A Curry ``Char`` is a Unicode code point.  A Python ``str`` converts to a
``String`` where a ``String`` is expected and a ``str`` of length one to a
``Char`` where a ``Char`` is expected (see :ref:`typed-expressions`); a
``String`` converts back to a ``str``.  Both directions keep every code
point.  The files that ``readFile``, ``writeFile``,
and ``appendFile`` touch hold UTF-8 on both backends.  So do the standard
streams of ``putChar`` and ``getChar`` on the C++ backend; on the Python
backend they use the encoding of ``sys.stdout`` and ``sys.stdin``.

:func:`curry.topython` takes an optional ``exprtype``, the static type of
the value in Curry syntax, and threads it through lists and tuples, so an
empty ``String`` converts to ``''``.  :func:`curry.eval` passes the type of
the goal it built to the converter.  Without a type, an empty list converts
to ``[]`` and a list of characters to a ``str``.

:func:`curry.topython` prunes the recursion wherever it encounters a
subexpression it cannot convert.  The reason for this potentially
counter-intuitive behavior is made clear by the following example:

    >>> just5 = curry.expr(Prelude.Just, 5)
    >>> curry.topython(just5)
    >>> <Just <Int 1>>

One might expect the boxed integer to be converted to a Python integer, but
that would lead to an ill-typed expression.  Sprite leaves it to the user to
avoid this or convert such values another way.

