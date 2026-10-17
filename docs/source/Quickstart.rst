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

Use ``install/bin/python`` and run the following examples from ``examples/``.

Importing and inspecting
========================

Run these examples from a directory containing ``Peano.curry`` (the file
in ``examples/``).  Imports search ``curry.path`` and the installed library.
The ``curry.lib`` import hook is also available.

    >>> import curry
    >>> curry.path.insert(0, '.')
    >>> P = curry.import_('Prelude')
    >>> Peano = curry.import_('Peano')
    >>> curry.import_('Peano') is Peano
    True
    >>> curry.modules['Peano'] is Peano
    True

A symbol is a term.  Calling it builds an application without evaluating it.
Operators and Python keywords are available through item lookup.
Metadata lives under ``curry.info(module)``; it includes the module's name,
file, symbols and types.  A type is metadata rather than a module attribute.

    >>> print(Peano.S)
    S
    >>> print(Peano.add)
    add
    >>> print(P['+'])
    (+)
    >>> curry.info(Peano).name
    'Peano'
    >>> sorted(curry.info(Peano).types)
    ['Nat']
    >>> [c.name for c in curry.info(Peano).types['Nat'].constructors]
    ['O', 'S']

Building terms
==============

A held ``Term`` describes a computation.  It is typed at construction and
remains unchanged by evaluation.  Partial applications are terms too.
Use ``curry.term`` for Python values and ``type=`` for an annotation.
A Python list always describes a list value, including a list of symbols.

    >>> goal = Peano.add(Peano.S(Peano.O), Peano.S(Peano.O))
    >>> print(goal)
    add (S O) (S O)
    >>> print(curry.eval(goal).one())
    S (S O)
    >>> print(goal)
    add (S O) (S O)
    >>> print(Peano.S(Peano.S(Peano.O)))
    S (S O)
    >>> curry.eval(P.length([Peano.O, Peano.O])).one()
    2
    >>> curry.eval(P.map(P['+'](1), [2, 3])).one()
    [3, 4]
    >>> curry.eval(curry.term(1, type='Float')).one()
    1.0

Curry text uses ``curry.parse``.  Imports are a sequence of modules or module
names.  Type annotations belong in the text.  A bare Python string passed
to evaluation is refused: choose text parsing or a String value explicitly.

    >>> parsed = curry.parse('add (S O) (S O)', imports=[Peano])
    >>> print(curry.eval(parsed).one())
    S (S O)
    >>> curry.eval(curry.parse('1 + 2 :: Int')).one()
    3
    >>> curry.eval(curry.term('hello')).one()
    'hello'

``curry.compile`` builds a module from source text.  The current session
lane uses ``name=`` when a specific module name is needed.

    >>> M = curry.compile('double :: Int -> Int\ndouble x = x + x', name='Double')
    >>> curry.eval(M.double(4)).one()
    8

Types and conversions
=====================

Construction reads the type schemes of symbols from their FlatCurry
interfaces, unifies the arguments, and supplies class dictionaries.
``curry.typeof`` returns Curry type text before defaulting.
``defaulted=True`` asks for the type evaluation will use.

    >>> curry.typeof(P['+'](1, 2))
    'Num a => a'
    >>> curry.typeof(P['+'](1, 2), defaulted=True)
    'Int'
    >>> curry.typeof([1, 2.5])
    '[Float]'
    >>> curry.typeof((1, 2.5))
    'Num a => (a, Float)'
    >>> curry.typeof(curry.term(1, type='Float'))
    'Float'

Python ``bool``, ``int`` and ``float`` become Bool, a numeric literal and
Float respectively.  An integer outside the signed 64-bit range is an
``IntOverflowError``.  A Python ``str`` is always a String; ``curry.Char``
spells a Char.  Lists are homogeneous, tuples have zero or two through
fifteen components, and ranges become lists.  An iterator is consumed
lazily; a type annotation can state its element type without consuming it.
Bytes, dictionaries, sets and None are refused.  Use explicit data such as
``P.Nothing`` or ``P.Just(x)`` for an optional value.

    >>> curry.eval(P.ord(curry.Char('a'))).one()
    97
    >>> curry.eval(P.length('a')).one()
    1
    >>> curry.eval(P.Just(3)).one().args
    (3,)
    >>> curry.eval(P.take(3, iter(range(10)))).one()
    [0, 1, 2]
    >>> curry.eval([1, 2.5]).one()
    [1.0, 2.5]

Class constraints default as in the PAKCS REPL: Num and Integral to Int,
Fractional and Floating to Float, Monad to IO, and a lone Data to Bool.
Other ambiguous constraints raise ``DefaultingError``.  A held partial
application has already been typed; a later call unifies with that type.

Errors
======

All public errors descend from ``curry.CurryError``, an Exception.
``CurryTypeError`` also derives from TypeError.  Its children distinguish
conversion, mismatch, arity, instance and type-annotation failures.
Construction errors name the argument and symbol.  Evaluation errors are
raised when the Results advances.  ``NoValueError`` and ``ManyValuesError``
are the two cardinality errors of ``one()``.

    >>> issubclass(curry.ConversionError, curry.CurryTypeError)
    True
    >>> issubclass(curry.CurryTypeError, TypeError)
    True
    >>> issubclass(curry.EvaluationError, curry.CurryError)
    True
    >>> P['not'](1)
    Traceback (most recent call last):
      ...
    curry.typecheck.errors.ConversionError: cannot convert 1 to Bool at argument 1 of Prelude.not :: Bool -> Bool: an int is a numeric literal; write True or False

Choices and sharing
===================

Each choice represents a nondeterministic computation.  One held Python
term used twice shares that computation.  Two separate reads of a function
symbol build independent computations.  The order of search values is the
scheduler's; sort when the order is irrelevant.

    >>> coin = curry.choice(0, 1)
    >>> sorted(curry.eval((coin, coin)))
    [(0, 0), (1, 1)]
    >>> sorted(curry.eval((curry.choice(0, 1), curry.choice(0, 1))))
    [(0, 0), (0, 1), (1, 0), (1, 1)]

Cycles can be written in Curry text.  Consume a finite prefix before
conversion: the outbound conversion is eager, with no lazy list view.

    >>> cycle = curry.parse('take 4 xs where xs = 1 : xs')
    >>> curry.eval(cycle).one()
    [1, 1, 1, 1]

Variables and answers
=====================

``curry.free(name)`` creates one named variable.  Reusing that Python object
shares the variable within a goal.  Bindings belong to an evaluation; the
variable's static type persists.  ``curry.anonymous`` creates a distinct
unnamed variable at every occurrence.  ``solve`` yields an ``Answer`` whose
``value`` is converted and whose ``bindings`` is a ``Bindings`` mapping,
indexed by name or by the original Var.  Evaluation alone yields values.

    >>> x = curry.free('x', type='Int')
    >>> goal = P['=:='](x, 3)
    >>> curry.eval(goal).one()
    True
    >>> answer = curry.solve(goal).one()
    >>> answer.value
    True
    >>> answer.bindings['x'], answer.bindings[x]
    (3, 3)
    >>> curry.show(answer)
    '{x=3} True'
    >>> curry.solve(P['=:='](x, 4)).one().bindings[x]
    4
    >>> goal = curry.parse('xs ++ [3] =:= [1,2,3] where xs free')
    >>> curry.show(curry.solve(goal).one())
    '{xs=[1,2]} True'
    >>> goal = curry.term((curry.anonymous, curry.anonymous), type='(Int, Int)')
    >>> list(curry.solve(goal).one().bindings)
    []

Results and outbound values
===========================

``curry.eval`` and ``curry.solve`` return a lazy ``Results`` iterator.
Nothing runs until it advances.  A break preserves its position; ``close``
ends the search, and a context manager closes it on exit.  ``one()`` checks
that exactly one value exists.  It reads a second value to detect ambiguity
and raises ``ManyValuesError`` if one exists.  Failure produces no value;
a suspension raises ``SuspensionError`` under ``EvaluationError``.

    >>> results = curry.eval(curry.choice(1, 2))
    >>> isinstance(results, curry.Results)
    True
    >>> next(results)
    1
    >>> list(results)
    [2]
    >>> with curry.eval(curry.choice(1, 2)) as results:
    ...   first = next(results)
    >>> first, list(results)
    (1, [])
    >>> list(curry.eval(P.failed))
    []

Built-in values become Python scalars, lists and tuples.  A Char remains a
``Char``, distinct in type from str but equal to the same one-character
string.  A user constructor becomes ``Data`` with ``symbol`` and ``args``;
a function value becomes a callable ``Function``.  Set functions produce a
finite multiset ``Values`` collection.  Converted values can enter later
Curry calls.  ``curry.show`` prints Curry text, including nested values;
Python's repr of a list follows Python's spacing and quoting.

    >>> value = curry.eval(P.Just([1, 2])).one()
    >>> isinstance(value, curry.Data)
    True
    >>> value.symbol.name, value.args
    ('Just', ([1, 2],))
    >>> curry.show(value)
    'Just [1,2]'
    >>> function = curry.eval(P['+'](1)).one()
    >>> isinstance(function, curry.Function)
    True
    >>> curry.eval(function(2)).one()
    3
    >>> curry.show(curry.eval(curry.term('', type='String')).one())
    '""'
    >>> SF = curry.import_('Control.SetFunctions')
    >>> values = curry.eval(SF.set0(curry.choice(1, 2))).one()
    >>> isinstance(values, curry.Values), sorted(values)
    (True, [1, 2])

A Python-held term shared inside and outside ``set0`` follows weak
encapsulation: whichever evaluation owns it first determines the result.
Use ``SF.set1(P.id, term)`` to put the choice outside deliberately.
A free argument narrows outside a set function, giving a set per binding.
The deferred failure rule produces no value only when nothing inside
succeeds and an outside failure is encountered.

Saving Compiled Curry
---------------------

:func:`curry.save` writes the compiled object of the current backend:

    >>> curry.save(Peano, 'Peano.so')

Load it in a new session. A second load of the same file returns the module
already registered under its name:

    >>> curry.reset()
    >>> Peano = curry.load('Peano.so')
    >>> curry.load('Peano.so') is Peano
    True

A file of another backend or format raises :class:`curry.LoadError`.
A name loaded from another file is refused too. To write a program that
prints the answers of a goal, name that goal with ``main``:

    >>> curry.save(Peano, 'peano.exe', main=Peano.main)

An import returns a loaded module unchanged. If its source changed,
:class:`curry.CurryWarning` says so once. :func:`curry.reload` reads the
source again and updates the module in place; earlier terms become stale.
A file module on the C++ backend under ``interpret='tiered'`` or ``'off'``
requires a new process, or ``curry.reset(interpret='new')`` before import,
for a reload. :func:`curry.wait` waits for background compilation.

.. _Python Tutorial: https://docs.python.org/3/tutorial/

