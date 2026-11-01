
Curry Types
===========

Curry is a strongly- and statically-typed language.  Its type system is based
on the classical `Hindley-Milner`_ formulation.  Every expression and defined
function has a definite static type, which Sprite and other Curry systems
check before the program runs.


Type inference
--------------

Curry uses a system of type inference whereby omitted types are deduced by the
compiler.  A broad class of programmer errors can be detected as errors in type
deduction.

Write a signature for every definition at module scope; the reader needs
it even when the compiler does not. The examples of this documentation do.

Function types
--------------

A function is an expression: it has a type and behaves like data. A call
supplies arguments. A call with fewer arguments than the function takes
is a function of the remaining ones; a call with all of them is evaluated
by the function's rules.

Function types are written in Curry with the ``->`` operator.  For example, the
type of a unary function that takes an integer, ``Int`` and returns an integer
can be written ``Int -> Int``.  An expression that applies this to an argument
of type ``Int`` has type ``Int``.  A binary function over integers has the type ``Int -> Int -> Int``.  Applying this to an integer produces an
expression of type ``Int -> Int``.  This process, called `currying`, is how
partial application is achieved.  Applying another ``Int`` produces an ``Int``.

A higher-order function is one that either takes a function as a parameter or
returns a function.  All other functions are first-order.  For example, a
higher-order function takes a unary function over integers
and an integer.  It applies the first argument to the second, returning an
integer.  Its type is ``(Int -> Int) -> Int -> Int``.
Alternatively, the type of a function that takes an integer and returns an
"increment" function that increments an integer by that amount is
as ``Int -> (Int -> Int)``.


Polymorphism
------------

Curry provides polymorphism through two constructs:

Polymorphic types
    Curry has a parametric type system. A type without parameters, such as
    Int, is a monomorphic type or monotype. A type with parameters, such
    as ``List a``, is a polymorphic type or polytype. Substituting a
    monotype for ``a`` gives a monotype: ``List Int`` and ``List String``
    are distinct monotypes. A function over ``List a``, for every ``a``,
    is polymorphic: one definition serves lists of every type.

Type classes
    A `type class <https://en.wikipedia.org/wiki/Type_class>`_ defines an
    interface of functions over several types. A type becomes an instance
    when an instance declaration implements that interface. The compiler
    selects the instance from the type at the call.

    ``Show`` supplies ``show``, ``Eq`` supplies ``==``, ``Num`` supports
    numeric literals, ``Ord`` supplies ordering for ``sortValues`` and
    ``Data`` supports free variables and functional patterns. The form
    ``Ord a => [a] -> [a]`` restricts ``a`` to instances of ``Ord``.

.. _Hindley-Milner: https://en.wikipedia.org/wiki/Hindley%E2%80%93Milner_type_system
.. _Type Classes: https://en.wikipedia.org/wiki/Type_class
