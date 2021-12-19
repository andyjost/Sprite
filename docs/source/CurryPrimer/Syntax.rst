.. highlight:: haskell

Curry Syntax
============

Curry's syntax is nearly identical to Haskell's.  This section provides a very
brief introduction that may help the unfamiliar get started.  The purpose is to
provide enough information to understand this document, plus the tests and
examples that come with Sprite.

Built-in Data Types
-------------------

Curry provides the following three fundamental types:

- ``Int``: Integer literals are written as one expects, e.g., ``0`` or ``1``,
  though negative integers are enclosed with parentheses, as in ``(-1)``.
  Syntactically, negative integers are simply negated positive integers.

- ``Char``: Character literals are enclosed in single quotes, as in ``'a'`` or
  ``'A'``.  Unicode and other escape sequences are recognized, as in some other
  programming languages.  So, for example, ``'\0'`` is the character with
  numeric code zero, usually referred to a NULL.

- ``Float``: Floating-point literals are written in the customary way; ``1.0``,
  ``1.`` or ``3.14159265``, for example.

Many other built-in types are provided by Curry.  Among these is a type ``Bool``
with constructors ``True`` and ``False``.  Curry also provides built-in lists
and tuples.  Lists are writen in one of two ways.  A complete list may be
witten enclosed in square brackets, as in ``[1, 2]``.  The empty list is
written ``[]``.  Alternatively, a nonempty list may be written in constructor
notation, as ``h:t``, where `h` is the `head` element and `t` is another list
called the `tail`.  Tuples are written enclosed within parentheses, as in
``('a', 1)``.  Curry has no 1-tuple.

User-Defined Data Types
-----------------------

Data types are defined with the ``data`` keyword.  For example, a type
representing a string of binary digits might be written as::

    data Binary = O Binary | I Binary | Null

``Binary`` has three `constructors`, namely ``O``, ``I``, and ``Null``.  These
represent the binary digits 0 and 1, and the end of the string, respectively.
``O`` and ``I`` each take one argument of type ``Binary``, whereas ``Null``
takes none.  Note that the self-reference makes ``Binary`` a recursive type,
and that a binary string of any length can be written.  To create an instance,
expressions of type ``Binary`` expressions are juxtaposed.  A few instances of
this type are as follows: ``Null``, ``I Null``, ``I (O Null)``.

Data type definitions may contain type variables, in which case the type
defined is a polytype.  The following definition of a list type illustrates::

    data List a = Cons a (List a) | Nil

Constructor ``Cons`` takes two arguments, an element of type ``a`` and a tail
of type ``List a``.  ``Nil`` terminates the list.  Like ``Binary``, ``List`` is
a recursive type and a list of any length can be defined.  Unlike ``Binary``,
the free type parameter allows one to build a list over any type.  A
monomorphic (i.e., concrete) list is formed by substituting ``a`` with a
monomorphic type.  For instance, ``List Int`` describes a list of integers,
which is monomorphic.

Defined Operations
------------------

User-defined operations are written using the `=` symbol.  For example::

    f = 42

``f`` evaluates to the integer ``42``.  For simplicity in this primer, we can
refer to defined operations as functions without losing much precision.

Functions are often annotated with their type.  The type annotation for ``f`` can
be written as follows::

    f :: Int

This says that ``f`` evaluates to type ``Int``.

Function arguments are written to the left of the `=` symbol.  Below, ``succ``
evaluates to the integer successor of a number, ``n``::

    succ n = n + 1

The type annotation of this function can be written as::

    succ :: Int -> Int

This means ``succ`` takes an ``Int`` and returns an ``Int``.

Rule Guards
...........

Functions may be made conditional by one or more Boolean expressions called
`guards`.  Guards are separated from the left-hand side of the definition by a
vertical bar, `|`.  The use of guards makes is possible to define functions in
piecewise fashion.  A function for calculating the absolute value of a number,
for instance, may be defined as follows::

    abs n | n<0  = -n
          | True = n

The guard expressions, ``n<0`` and ``True`` are evaluated sequentially from top
to bottom and when one evaluates to true the corresponding rule is fired.


Pattern Matching
................

So far, each function argument has been a variable.  More generally, the
arguments in a function definition are patterns.  A pattern is an expression
involving variables and/or constructors.  By using multiple patterns, a
function can be written as a set rules.  When evaluating such a function, the
patterns are compared with the actual argument provided to determine which rule
to fire.  (For now, we will assume that only one rule ever matches, though this
is a simplification.)

To illustrate, we can write write a function ``isNull`` that indicates whether
a ``Binary`` argument has any digits at all::

    isNull Null = True
    isNull I _  = False
    isNull O _  = False

.. note::
   ``_`` is a placeholder for an anonymous variable.

When ``isNull`` is called, the ``Binary`` argument is inspected and only the
matching rule is fired.  Thus, ``isNull Null`` evaluates to ``True``, whereas
``isNull (I Null)`` evaluates to ``False``.

Curry supports another kind of function definition.  When a pattern contains a
function application, it is called a `functional pattern`.  This provides a
useful way to describe data constructively.

The following example implements a data store as a list of key-value pairs.
Function ``find`` uses a functional pattern to select all values with a given
key::

    data Data a = [(String, a)]

    find :: String -> Data -> a
    find key (_ ++ (key, value) ++ _) = value

This pattern uses the list append function, ``++``, to build any list
containing a pair with the supplied key.  When this rule matches, ``find``
evaluates to the corresponding value.


Other Constructs
----------------

Curry inherts other syntactic constructs from Haskell.  A few of these are
discussed below (though the list is by no means exhaustive):

``let`` expressions
...................

`let` expressions introduce and bind local variables.

Example::

    poly n = let a=n+1 in a*a

The above defines a function ``poly`` that evaluates to the polynomial expression
``(n+1) * (n+1)``.  ``a`` is a local variable.

Multiple bindings are permitted, as in::

    poly' n = let a=(n+1), b=(n-1) in a*b

``case`` expressions
.....................

A `case` expression performs pattern matching in an expression context.  For
example, another way to write ``isNull`` is as follows:

Example::

    isNull'' binary = case binary of
        (O _) -> False
        (I _) -> False
        Null  -> True

.. note::
   Single quotes may appear at the end of an identifier.  This is often used to
   suggest multiple versions of an entity.

``where`` clauses
.................

A block of local definitions can be introduced by the ``where`` keyword.  The
definitions are visible only to the enclosing function.

Example:

The following code block defines a function to return every other element of a
list.  An auxiliary function, ``skip``, is defined in a ``where`` clause::

    everyOther [] = []
    everyOther (h:t) = h:everyOther (skip t)
        where skip [] = []
              skip (h':t') = t'

If-Then-Else expressions
........................

This construct is syntactic sugar for a pattern match over a Boolean
expression.  ``abs``, for example, can be written as follows::


    abs' n = if n<0 then (-n) else n

This could be written equivalently using a `case` expression as::

    abs'' n = case n<0 of
        True  -> (-n)
        False ->   n

