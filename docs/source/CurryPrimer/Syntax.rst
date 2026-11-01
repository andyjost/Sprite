.. highlight:: haskell

Curry Syntax
============

Curry's syntax is close to Haskell's. This page gives enough of it to
read the examples and tests of Sprite.

Built-in data types
-------------------

Curry provides the following three fundamental types:

- ``Int``: An integer literal is written ``0`` or ``1``,
  though negative integers are enclosed with parentheses, as in ``(-1)``.
  Syntactically, negative integers are negated positive integers.

- ``Char``: Character literals are enclosed in single quotes, as in ``'a'`` or
  ``'A'``.  Unicode and other escape sequences are recognized, as in some other
  programming languages.  So, for example, ``'\0'`` is the character with
  numeric code zero, usually called NUL.

- ``Float``: Floating-point literals are written in the customary way; ``1.0``,
  ``3.14159265``, for example. A float literal has digits on both sides
  of the point.

Many other built-in types are provided by Curry.  Among these is a type ``Bool``
with constructors ``True`` and ``False``.  Curry also provides built-in lists
and tuples.  Lists are written in one of two ways.  A complete list may be
written enclosed in square brackets, as in ``[1,2]``.  The empty list is
written ``[]``.  Alternatively, a nonempty list may be written in constructor
notation, as ``h : t``, where ``h`` is the head and ``t`` is another list
called the `tail`.  Tuples are written enclosed within parentheses, as in
``('a', 1)``.  Curry has no 1-tuple. A ``String`` is a list of ``Char``: ``"ab"`` is
``['a','b']``.

User-defined data types
-----------------------

Data types are defined with the ``data`` keyword.  For example, a type
representing a string of binary digits might be written as::

    data Binary = O Binary | I Binary | Null

``Binary`` has three `constructors`, namely ``O``, ``I`` and ``Null``.  These
represent the binary digits 0 and 1 and the end of the string, respectively.
``O`` and ``I`` each take one argument of type ``Binary``, whereas ``Null``
takes none. The self-reference makes ``Binary`` a recursive type, so a
binary string of any length is a value. A value is built by applying
constructors: ``Null``, ``I Null``, ``I (O Null)``.

Data type definitions may contain type variables, in which case the type
defined is a polytype.  The following definition of a list type illustrates::

    data List a = Cons a (List a) | Nil

Constructor ``Cons`` takes two arguments, an element of type ``a`` and a tail
of type ``List a``.  ``Nil`` terminates the list.  Like ``Binary``, ``List`` is
a recursive type and a list of any length can be defined.  Unlike ``Binary``,
the type variable allows a list to hold values of any type.  A
monomorphic list is formed by substituting ``a`` with a
monomorphic type.  For instance, ``List Int`` describes a list of Int,
which is monomorphic.

Defined operations
------------------

This primer calls defined operations functions. A function definition
uses ``=``. A type signature states its type::

    f :: Int
    f = 42

Function arguments stand to the left of ``=``. ``succ`` takes an Int and
returns an Int::

    succ :: Int -> Int
    succ n = n + 1

Rule guards
...........

Functions may be made conditional by one or more Boolean expressions called
`guards`.  Guards are separated from the left-hand side of the definition by a
vertical bar, `|`.  The use of guards makes it possible to define functions in
piecewise fashion.  A function for calculating the absolute value of a number,
for instance, may be defined as follows::

    abs :: Int -> Int
    abs n | n < 0  = -n
          | True = n

The guard expressions, ``n < 0`` and ``True`` are evaluated sequentially from top
to bottom and when one evaluates to true the corresponding rule is fired.


Pattern matching
................

A pattern is an expression of variables and constructors. A function
with several rules has a pattern per rule and its argument selects the
matching rules (:ref:`CurryPrimer/Semantics:Overlapping rules`). The
function ``isNull`` tells whether a ``Binary`` has any digit::

    isNull :: Binary -> Bool
    isNull Null  = True
    isNull (I _) = False
    isNull (O _) = False

The pattern ``_`` is an anonymous variable: it matches anything and binds
nothing.

When ``isNull`` is called, the ``Binary`` argument is inspected and only the
matching rule is fired.  Thus, ``isNull Null`` evaluates to ``True``, whereas
``isNull (I Null)`` evaluates to ``False``.

Curry supports another kind of function definition.  When a pattern contains a
function application, it is called a `functional pattern`.  This provides a
useful way to describe data constructively.

The following example implements a data store as a list of key-value pairs.
Function ``find`` uses a functional pattern to select all values with a given
key::

    type Store a = [(String, a)]

    find :: Data a => String -> Store a -> a
    find key (_ ++ [(key, value)] ++ _) = value

This pattern uses the list append function, ``++``, to build any list
containing a pair with the supplied key.  When this rule matches, ``find``
evaluates to the corresponding value; with two pairs under the key, it has
two values::

    find "b" [("a",1),("b",2),("c",3)]   -- 2
    find "b" [("a",1),("b",2),("b",3)]   -- 2, 3

The constraint ``Data a`` is required: the match unifies the pattern with
the argument and the Curry front end rejects the signature without it.

What the match does is on :doc:`Semantics`; :doc:`/Status` describes
the cost of using values that a functional pattern builds.

Other constructs
----------------

Curry inherits ``let``, ``case``, ``where`` and if-then-else from Haskell.

``let`` expressions
...................

A ``let`` expression introduces and binds local variables::

    poly :: Int -> Int
    poly n = let a = n + 1 in a * a

The above defines a function ``poly`` that evaluates to the polynomial expression
``(n + 1) * (n + 1)``.  ``a`` is a local variable.

Several bindings are separated by semicolons or written one per line::

    poly' :: Int -> Int
    poly' n = let a = n + 1; b = n - 1 in a * b

``case`` expressions
.....................

A ``case`` expression performs pattern matching inside an expression.
Another way to write ``isNull`` is::

    isNull'' :: Binary -> Bool
    isNull'' binary = case binary of
        O _ -> False
        I _ -> False
        Null  -> True

A prime at the end of a name, as in ``isNull''``, marks a variant.

``where`` clauses
.................

A block of local definitions can be introduced by the ``where`` keyword.  The
definitions are visible only to the enclosing function.

The following function returns every other element of a list. Its
auxiliary function, ``skip``, is defined in a ``where`` clause::

    everyOther :: [a] -> [a]
    everyOther [] = []
    everyOther (h:t) = h : everyOther (skip t)
        where skip [] = []
              skip (h':t') = t'

If-then-else expressions
........................

This construct is syntactic sugar for a pattern match over a Boolean
expression.  ``abs``, for example, can be written as follows::


    abs' :: Int -> Int
    abs' n = if n < 0 then (-n) else n

The equivalent ``case`` expression is::

    abs'' :: Int -> Int
    abs'' n = case n < 0 of
        True  -> (-n)
        False ->   n
