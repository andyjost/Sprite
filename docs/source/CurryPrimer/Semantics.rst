.. highlight:: haskell

Curry Semantics
===============

This section describes the parts of the semantics of Curry that a reader
of this document meets most often: non-determinism, free variables, and
set functions.  The outputs shown are the values Sprite gives for the
expressions, in the order the REPL printed them.

Non-Determinism
---------------

A Curry expression can have several values.  The simplest source of
several values is the choice operator ``?``::

    coin :: Int
    coin = 0 ? 1

``coin`` has the values ``0`` and ``1``.  An evaluation of ``coin`` in
Sprite yields both, one after the other; a program that needs one of them
takes the first and discards the rest.

Choices
.......

A choice is a value, not an action.  The two occurrences of ``coin`` in
``coin + coin`` are two independent choices, so the expression has four
values::

    coin + coin   -- 0, 1, 1, 2

A variable bound to a choice is one choice, shared by every use of the
variable.  This is call-time choice, the rule of Curry::

    let c = coin in c + c   -- 0, 2

Sprite implements it with pull-tabbing: a choice is moved to the root of
the expression step by step, and the two alternatives share every part
that the choice did not touch.  The same rule applies to a parameter: a
function called with ``coin`` sees one value of it, whatever the function
does with the parameter.

Overlapping Rules
.................

A function whose rules overlap is non-deterministic too.  Every rule
that matches contributes its values.  ``insert`` places an element at
every position of a list, and ``perm`` gives every permutation::

    insert :: a -> [a] -> [a]
    insert x xs     = x : xs
    insert x (y:ys) = y : insert x ys

    perm :: [a] -> [a]
    perm []     = []
    perm (x:xs) = insert x (perm xs)

    perm [1,2,3]
    -- [1, 2, 3], [2, 1, 3], [1, 3, 2], [3, 1, 2], [2, 3, 1], [3, 2, 1]

A rule whose guard fails, or a pattern that matches nothing, contributes
no value.  An expression with no value at all fails; a failure is not an
error, and the other alternatives of a search go on.  Search in Curry is
the evaluation of such expressions: a generator produces the candidates
as values, and a guard removes the ones that do not fit.

Free Variables
--------------

A variable declared ``free`` has no value until the computation binds it.
The equational constraint ``=:=`` binds a variable to make both sides
equal::

    xs ++ [3] =:= [1,2,3] where xs free   -- {xs=[1, 2]} True

A function applied to a free variable narrows it: the variable is
instantiated with each constructor of its type that lets a rule match,
one alternative per constructor.  Arithmetic and comparison on a free
variable of a built-in type do not narrow it; the evaluation suspends
until another part of the computation binds the variable (see
:ref:`typed-expressions` for the same rule seen from Python).  A free
variable must have a ``Data`` type, so a function type cannot be free.  A
function whose rule unifies a value of a polymorphic type, as a functional
pattern does, carries a ``Data a =>`` constraint in its signature.

Functional Patterns
...................

A functional pattern is a pattern that contains a function call.  The
rule matches an argument that the call can produce, and the variables of
the pattern are bound to the pieces::

    last' :: Data a => [a] -> a
    last' (_ ++ [x]) = x

    last' [1,2,3]   -- 3

The match is a search over the values of the pattern: ``_ ++ [x]`` is
narrowed until it equals the argument.  The variables a functional pattern
binds stay narrowed in the result; the note under
:ref:`CurryPrimer/Syntax:Pattern Matching` gives the cost of that and the
idiom that avoids it.

Set Functions
-------------

A set function collects the values of a function into a set, so a program
can ask whether a search has a solution, how many, or which is the
smallest, without leaving the program.  ``set1 f`` is the set function of
the unary ``f``, and ``set0`` to ``set7`` cover the other arities.  The
module ``Control.SetFunctions`` provides them with ``sortValues``,
``isEmpty`` and the other operations on a set.  The prompt of the REPL
sees the loaded module and the Prelude alone (see :ref:`repl`), so the
examples of this section are definitions of the module::

    import Control.SetFunctions

    f :: Int -> Int
    f x = x ? (x + 1)

    main1 = sortValues (set1 f 1)   -- [1, 2]

The set function encapsulates the non-determinism of the body of ``f``:
the two values of ``f 1`` are the elements of one set.  The
non-determinism of the argument is not encapsulated.  A choice that comes
from outside the call produces one set per alternative, and the choice is
shared with the rest of the expression, as call-time choice requires::

    main2 = sortValues (set1 f (1 ? 5))                  -- [1, 2], [5, 6]
    main3 = sortValues (set1 id (1 ? 2))                 -- [1], [2]
    main4 = let x = 1 ? 2 in (x, sortValues (set1 f x))  -- (1, [1, 2]), (2, [2, 3])

In the last line each value of ``x`` goes with the set computed from that
value.  The same holds for a free variable that the argument holds.  A set
function that starts before the variable is bound, and resumes after
another alternative narrowed it, computes its set from the binding of its
own alternative (the repair of issue #61).

The same holds for a choice or a free variable that the function value
holds.  A partial application holds the arguments given so far, and a
lambda that closes over a variable of the enclosing context holds it as an
argument after lambda lifting; Sprite boxes those arguments as it boxes the
arguments of the call, so their non-determinism stays outside the set
(issue #117)::

    main6 = let x = 1 ? 2 in (sortValues (set1 (\y -> x + y) 10), x)
                                                  -- ([11], 1), ([12], 2)

``captureS`` of ``Control.SetFunctions`` is the explicit way to put the
non-determinism of an argument inside the set: ``evalS (set f `captureS`
(1 ? 2))`` has one value, the set of ``f 1`` and ``f 2`` together.

A function whose result is a failure has the empty set::

    source :: String -> String
    source (stem ++ ".o") = stem ++ ".c"

    main5 = isEmpty (set1 source "main.c")   -- True

A failure that comes from an argument gets the same treatment by default:
``isEmpty (set1 id failed)`` is ``True``.  The interpreter flag
``setfunction_failures`` set to ``'escape'`` makes such a failure fail the
set function instead, as the semantics of weakly encapsulated search
prescribes; a failure of the function's own body still gives the empty set,
and an argument the function does not demand fails nothing.

Sprite evaluates a set function lazily by default: the values of the set
are computed as the program consumes them (the interpreter flag
``setfunction_strategy``).  Inside the set, the scheduler runs a queue of
its own, and the rotation of the Fair Scheme covers the nested queues, so
an alternative that diverges inside a set function does not starve the
others.
