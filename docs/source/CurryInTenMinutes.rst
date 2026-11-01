====================
Curry in ten minutes
====================

You have read the README, or the end of a lesson sent you here, and you
have ten minutes. This page teaches the Curry you need to read the
lessons. Each idea gets one small Curry module, the Python that calls it,
and the printed result as a comment, exactly as a run printed it. Every
block runs after :doc:`installation <Installation/Installation>` with
``pip install --pre curry``; the flag selects the pre-release, since
Sprite is in alpha. The wheel holds the runtime and the compiled Curry
library, and its one dependency, ``curry-frontend``, holds the front end
that reads your ``.curry`` files; no C++ compiler is needed. Save the
``.curry`` files in the directory where you start Python.

A type and its equations
========================

Start with the part that resembles a tagged union and a ``match``
statement. A ``data`` declaration lists the ways to build a value, and a
function is a set of equations, one for each shape of its argument. Here
is a small expression type with an evaluator:

.. code-block:: haskell

   -- Expr.curry
   data Expr = Lit Int | Add Expr Expr | Mul Expr Expr

   calc :: Expr -> Int
   calc (Lit n) = n
   calc (Add a b) = calc a + calc b
   calc (Mul a b) = calc a * calc b

``--`` starts a comment. The bar in the ``data`` line separates the
alternatives of the type: ``Lit``, ``Add`` and ``Mul`` are its
constructors, each followed by the types of its fields. The line with
``::`` is the signature of ``calc``: it takes an ``Expr`` and returns an
``Int``. A call is the function followed by its arguments, with spaces
and no parentheses, and it binds tighter than an operator, so
``calc a + calc b`` is ``calc(a) + calc(b)``. The constructor of the
argument selects one of the three equations. Save the file beside your
Python and call it:

.. code-block:: python

   import curry
   curry.path.insert(0, '.')            # '.' is not searched by default
   from curry.lib import Expr as E      # translates Expr.curry, once

   e = E.Add(E.Lit(1), E.Mul(E.Lit(2), E.Lit(3)))
   print(f'{e} = {curry.eval(E.calc(e)).one()}')
   # Add (Lit 1) (Mul (Lit 2) (Lit 3)) = 7

You build ``e`` in Python from the constructors on the module, and it
prints in Curry's notation. ``E.calc(e)`` builds the call and checks its
argument against the signature; nothing runs until ``curry.eval`` asks
for the values. ``.one()`` says that you expect exactly one value and
returns it as a Python ``int``. The first import of a module runs the
Curry front end and saves its products in a ``.curry`` directory beside
the file, under a second for each module here in our run; a later import
reads them, and the runtime interprets the module.

A function with several values
==============================

A Curry expression can have more than one value. The
operator ``?`` makes a choice: ``a ? b`` has the values of ``a`` and the
values of ``b``.

.. code-block:: haskell

   -- Tile.curry
   tile :: Int
   tile = 16 ? 32 ? 64

``tile`` has three values, and Python sees them as an iterator:

.. code-block:: python

   from curry.lib import Tile as T

   for t in curry.eval(T.tile):
       print(t)
   # 16
   # 32
   # 64

   try:
       curry.eval(T.tile).one()
   except curry.ManyValuesError:
       print('tile has more than one value')
   # tile has more than one value

This is nondeterminism: an expression stands for all of its values, and
the runtime finds them. Each value comes out of its own computation, one
path through the choices, which we call an alternative. Unlike a list,
``tile`` asks nothing of its users: ``fits n tile`` below is written for
one ``Int`` and gets one value per tile.

The runtime evaluates by rewriting: it replaces a call by the right side
of the equation that matches, one step at a time. The strategy that
chooses the steps, the Fair Scheme, is proved sound, complete, and
optimal; the proofs are in the `dissertation
<https://doi.org/10.15760/etd.3564>`_. For you it means that every value
that comes out is a value of the expression, that every value the
expression has comes out, and that no step runs that no value needs;
optimal counts rewrite steps and says nothing about seconds. An
alternative that never finishes can't hide the others; they still arrive
as you iterate. After the last one, the next pull waits forever, so
``list`` over such a goal, the expression you hand to ``curry.eval``,
never returns; take what you need with ``next`` or ``itertools.islice``.

One choice, shared
==================

``tile`` has no parameters, but it is still a function: each mention of it
is a call, and each call makes its own choice. A variable bound to
``tile`` makes the choice once, however often the variable is used:

.. code-block:: haskell

   -- Tile.curry, continued
   pair :: (Int, Int)
   pair = (tile, tile)

   square :: (Int, Int)
   square = (t, t) where t = tile

.. code-block:: python

   print(len(list(curry.eval(T.pair))))     # 9
   print(list(curry.eval(T.square)))        # [(16, 16), (32, 32), (64, 64)]

``(Int, Int)`` is the type of a pair. ``pair`` has nine values, every
combination. ``square`` has three, because ``t`` is one value inside one
computation. ``where t = tile`` defines ``t`` for the equation above it;
``let t = tile in (t, t)`` does the same inside an expression. A
parameter is one value too: a function called with ``tile`` sees a single
tile, however many times its body uses it. Curry calls this rule
call-time choice.

No value at all
===============

An expression can also have no value. A guard that is false and a pattern
that doesn't match both end their alternative, and nothing is raised:

.. code-block:: haskell

   -- Tile.curry, continued
   fits :: Int -> Int -> Int
   fits n t | n `mod` t == 0 = t

   only :: [Int] -> Int
   only [t] = t

``fits`` takes two arguments: in a signature each ``->`` ends one
parameter, and the last type is the result. ``mod`` in backticks is the
function ``mod`` written between its arguments. The bar after the
parameters introduces a guard, the second meaning of that symbol:
``fits n t`` is ``t`` when ``t`` divides ``n`` and has no value otherwise.
``[Int]`` is a list of ``Int``; ``only`` has one equation, for a list of
exactly one element.

.. code-block:: python

   print(list(curry.eval(T.fits(96, T.tile))))    # [16, 32]
   print(list(curry.eval(T.fits(100, T.tile))))   # []
   print(list(curry.eval(T.only([16, 32]))))      # []

In ``fits 96 tile`` the parameter ``t`` is one tile per computation, and
the computation with 64 has no value; for 100 none has, and ``only`` of a
two-element list matches no equation. Python sees an empty iterator in
both cases, with no exception and no placeholder; ``.one()`` raises
``NoValueError`` there. This is how a search prunes itself: an
alternative that can't produce a value drops out, and the others go on.
A missing equation looks the same as an empty search, and Sprite reports
no warning for it; when a function should cover every case, test that it
does.

A free variable
===============

A variable declared ``free`` has no value until the computation binds it.
Here is a state machine and a function that runs it in the other
direction:

.. code-block:: haskell

   -- Machine.curry
   data State = Idle | Busy | Done

   step :: State -> State
   step Idle = Busy
   step Busy = Busy ? Done

   origin :: State -> State
   origin t | step s =:= t = s where s free

In the last line, ``origin t`` is ``s`` when the guard ``step s =:= t``
holds, and ``where s free`` after the body declares ``s`` as a free
variable. ``=:=`` is the equational constraint: it binds free variables
so that both sides become equal, and it fails when they can't. The ``==``
of ``fits`` is the Boolean test you know, with a value on each side; when
a side holds a free variable that you want bound, write ``=:=``. To
evaluate ``step s`` with ``s`` free, the match in ``step`` needs a
constructor, so the computation splits into one alternative per
constructor of ``State``, with ``s`` bound in each; the guard keeps the
alternatives whose step is ``t``. A free ``Int`` has no constructors to
split on: ``x =:= 5`` binds it, and arithmetic on it waits for a binding,
which Python reports as ``SuspensionError`` when none comes.

.. code-block:: python

   from curry.lib import Machine as M

   print(list(curry.eval(M.origin(M.Busy))))   # [Idle, Busy]

   s = curry.free('s')
   for value, bindings in curry.solve(M.step(s)):
       print(f'{bindings[s]} -> {value}')
   # Idle -> Busy
   # Busy -> Busy
   # Busy -> Done

Python can make a free variable too: ``curry.free`` returns a ``Var``,
which you pass into a call like any other argument. ``curry.solve`` is
``curry.eval`` with the bindings: each answer pairs a value with a mapping
from every ``Var`` in the goal to what the computation bound it to,
indexed by the ``Var`` or by its name.

A function run backwards
========================

``origin`` wrote the search out by hand. Curry has a shorthand for exactly
this: put the call in the pattern.

.. code-block:: haskell

   -- Machine.curry, continued
   before :: State -> State
   before (step s) = s

A pattern that contains a function call is a functional pattern: it
matches an argument that the call can produce and binds the variables of
the call to the values for which the call produces it. To match
``before Done``, the runtime solves for the ``s`` whose ``step`` is
``Done``, by the splitting you just saw.

.. code-block:: python

   print(list(curry.eval(M.before(M.Done))))   # [Busy]
   print(list(curry.eval(M.before(M.Idle))))   # []

   match curry.eval(M.before(M.Done)).one():
       case M.Busy: print('Busy comes before Done')
   # Busy comes before Done

Nothing steps to ``Idle``, so ``before Idle`` has no value. A value of
your own type comes back as Python data too: ``Busy`` is ``M.Busy``
itself, which ``==`` and a ``match`` statement recognize. The `README
<https://github.com/andyjost/Sprite#running-a-function-backwards>`_
builds a parser from a printer with the same one-line form,
``parse (render p) = p``. When you have one direction of a relation as a
function, this is how you get the other one. The argument bounds the
search, whatever the size of the type: ``render p`` is built only as far
as the argument's characters demand, and a candidate whose first
character disagrees is dropped there. Formulas are infinite in number,
and the README's string parses in about a millisecond once the module
is loaded, in our run.

The set of values, as a value
=============================

Inside Curry a choice is never local: each value of a subexpression is a
separate alternative of the whole program, and Python meets them one at
a time. Sometimes the program itself needs them all at once, to test for
any or pick the largest. A set function collects the
values of one call into a set; ``Control.SetFunctions``, which provides
them, ships with the package.

.. code-block:: haskell

   -- Fit.curry
   import Control.SetFunctions
   import Tile

   fitting :: Int -> Int
   fitting n = fits n tile

   allFits :: Int -> [Int]
   allFits n = sortValues (set1 fitting n)

   hasFit :: Int -> Bool
   hasFit n = not (isEmpty (set1 fitting n))

   outside :: Int -> [Int]
   outside n = sortValues (set2 fits n tile)

``fitting n`` is a tile that fits ``n``, one value for each tile that
does. ``set1 fitting`` is its set function: ``set1 fitting n`` is the set
of those values; ``sortValues`` lists a set in order, ``isEmpty`` tests
it, and ``not`` negates a ``Bool``. The number in ``set1`` is the arity,
which a type doesn't fix: ``Int -> Int -> Int`` is both a two-argument
function and a one-argument function that returns a function, so the
library spells the count out, ``set0`` to ``set7``.

.. code-block:: python

   from curry.lib import Fit as F

   print(curry.eval(F.allFits(96)).one())   # [16, 32]
   print(curry.eval(F.hasFit(100)).one())   # False
   print(list(curry.eval(F.outside(96))))   # [[16], [32], []]

``allFits`` and ``hasFit`` have exactly one value now, so ``.one()`` is
right. The set collects the choices made inside the call; a choice made
in an argument stays outside it, so ``outside 96``, which passes ``tile``
as an argument, has three values, one set per tile, and the tile that
doesn't fit gives the empty set. That is why ``fitting`` puts ``tile``
inside its body.

Laziness
========

Curry evaluates an expression only as far as a result demands. That is
what lets ``parse`` stop at a wrong first character; it also lets a list
be infinite:

.. code-block:: haskell

   -- Lazy.curry
   powers :: [Int]
   powers = 1 : map (* 2) powers

   firstPowers :: Int -> [Int]
   firstPowers n = take n powers

.. code-block:: python

   from curry.lib import Lazy as L

   print(curry.eval(L.firstPowers(8)).one())   # [1, 2, 4, 8, 16, 32, 64, 128]

``:`` puts an element in front of a list, ``(* 2)`` is the function that
doubles its argument, and ``map`` applies it to every element, so
``powers`` is 1 followed by the doubles of ``powers`` itself. ``take 8``
builds only the eight cells it needs. Python receives finished values, so
ask Curry for a prefix, as here; the whole infinite list would never
arrive.

The Python boundary in one place
================================

Every block above crossed the boundary the same way:

.. code-block:: python

   import curry
   from itertools import islice
   curry.path.insert(0, '.')            # '.' is not searched by default
   from curry.lib import Tile as T      # translates Tile.curry, once

   goal = T.fits(96, T.tile)            # a typed term; nothing has run
   print(goal)                          # fits 96 tile
   results = curry.eval(goal)           # a lazy iterator; still nothing runs
   print(next(results, None))           # 16
   print(list(results))                 # [32]
   print(list(islice(curry.eval(T.tile), 2)))   # [16, 32]
   text = curry.parse('fits 96 tile', imports=[T])
   print(list(curry.eval(text)))        # [16, 32]

``curry.path`` is the list of directories where ``.curry`` files are
found, like ``sys.path``; it holds the installed library and whatever
``CURRYPATH`` names, so add the directory where you start Python.
``from curry.lib import M`` translates ``M.curry``, as the first section
described, and the module's functions and constructors are attributes of
``M``. A call such as ``T.fits(96, T.tile)`` builds a term and checks the
arguments against the signature; a mismatch raises ``CurryTypeError``
there, before anything runs. ``curry.parse`` builds the same term from
Curry text, which is handy at a prompt; in a program, use the call form,
which Python checks. ``curry.eval`` returns the values as a lazy
iterator: ``.one()`` for exactly one, ``next(results, None)`` for the
first or ``None``, ``islice`` for a bounded number, a ``for`` loop or
``list`` for all of them when every alternative finishes. ``curry.solve``
returns the same values paired with the bindings of the ``Var`` objects
in the goal. Values come back as Python data: ``int``, since Curry's
``Int`` is unbounded like Python's, ``float``, ``str``, lists and tuples,
and instances of your own types for ``isinstance`` and ``match``.

Where to go next
================

Three lessons take these ideas to problems you recognize.
:ref:`Lesson 24 <example-24>` writes the rules of a build as equations and
asks them in both directions, what a target needs and what a changed file
touches. :ref:`Lesson 15 <example-15>` states in one function when a
package plan is consistent and lets the runtime find the plans, and the
same relation explains why a resolution failed. :ref:`Lesson 21
<example-21>` writes the overload resolution rules of C++ over a model of
its types and then asks which argument types would make a call ambiguous.
The :doc:`CurryPrimer/index` is the reference for what you saw here, and
:doc:`PythonAPI/UsingTheAPI` follows the boundary from the first call to
streams.
