
The Curry Type System
=====================

Curry is a strongly- and statically-typed language.  Its type system is based
on the classical `Hindley-Milner`_ formulation.  Every expression and defined
operation has a definite static type, so Curry can be statically compiled by
Sprite and other Curry systems.


Type Inferrence
---------------

Curry uses a system of type inferrence whereby ommitted types are deduced by
the compiler.  A broad class of programmer errors can be detected as errors in
type deduction.

Type inferrence can significanly reduce visual clutter by allowing the
programmer to omit redundant details.  If taken to far, however, this can
become inconvenient.  For instance, someone reading Curry code may wish to know
the type of a function.  If this is not written down, then that person must
resort to performing type inferrence mentally.

To balance these considerations, it is customary to write type annotations
wherever it improves readability and especially for definitions at module
scope.


Function Types
--------------

Functions in Curry are first-class citizens.  Functions are expressions,
meaning they have a type and behave like data.  A function can be applied by
supplying arguments.  If fewer than the requisite number of arguments is
supplied, the result is another function-like expression with another type.  If
all arguments are supplied, the function-rooted expression is evaluated via
pattern-matching to the right-hand side of one of its rules.

Function types are written in Curry with the ``->`` operator.  For example, the
type of a unary function that takes an integer, ``Int``, and returns an integer
can be written ``Int -> Int``.  An expression that applies this to an argument
of type ``Int`` has type ``Int``.  A binary function over integers would be
written ``Int -> Int -> Int``.  Applying this to an integer produces an
expression of type ``Int -> Int``.  This process, called `currying``, is how
partial application is achieved.  Applying another ``Int`` produces an ``Int``.

As in any functional language, we may regard all expressions as functions.  For
example, an expression of type ``Int`` can be regarded as a function that takes
nothing and returns an integer.

A higher-order function is one that either takes a function as a parameter or
returns a function.  All other functions are first-order.  For example, a
higher-order function could be defined to take a unary function over integers
and an integer.  It applies the first argument to the second, returning an
integer.  Its type would be written ``(Int -> Int) -> Int -> Int``.
Alternatively, the type of a function that takes an integer and returns an
"increment" function that increments an integer by that amount would be written
as ``Int -> (Int -> Int)``.


Polymorphism
------------

Curry provides polymorphism through two constructs:

`polymorphic types`
    Curry uses a parameteric type system.  A simple, unparameterized type such as
    an integer is called a `monomorphic type` or `monotype`.  Parameterized types
    are called `polymorphic types` or `polytypes`.  For example, the type ``List
    a`` is a polytype because it takes a type parameter, ``a``.  To create a
    monomorphic list, one binds a monotype to ``a``.  If the monotype
    ``Int``, representing an integer, is defined then ``List Int`` is a monotype.

    Each concrete instance of a list, such as a list-of-integers or
    list-of-strings, is a distinct monotype.  Since it is, in principle,
    possible to build a list of anything, a function operating over a family of
    lists is polymorphic.  For instance, if several numeric types are defined,
    a function that sums the elements of a list might be able to accept any
    numeric list; hence, it is polymorphic.

`Type Classes`
    `Type Classes`_ enable ad-hoc polymorphism in which a function
    implementation is selected based on the argument types provided at the call
    site.  In the simplest cases, type classes provide a capability similar to
    function overloading.  A type class defines a set of functions, i.e., an
    interface, that may be applied to arguments of a variety of types.  To use
    an arbitrary type as a instance of the type class, a programmer implements
    the interface for that type.

    To see this in more concrete terms, consider a Type Class `Hashable` that
    defines a single function `hash`.  This function takes an arbitrary
    argument and returns an integer representing its hash.  A programmer
    wishing to hash a particular type, say a list of integers, first provides
    an instance declaration that implements `hash` for lists of integers.
    Instances can be provided for any number of types, and it is the compiler's
    job to decide which version to use in any particular case.

.. _Hindley-Milner: https://en.wikipedia.org/wiki/Hindley%E2%80%93Milner_type_system
.. _Type Classes: https://en.wikipedia.org/wiki/Type_class
