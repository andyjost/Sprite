
The Curry Type System
=====================

Curry is a strongly-typed language whose typing scheme is based on the
classical `Hindley-Milner Type System`_.  Every expression and defined
operation has a definite static type.  As such, Curry can be statically
compiled by Sprite and other Curry systems.

Polymorphism is achieved by two constructs:

`polymorphic types`
-------------------

A simple type such as an integer is called a `monotype`.  Monotypes take no
type parameters.  By contrast, parameterized types are called `polymorphic
types` or `polytypes`.  A polymorphic type takes at least one type parameter.
A simple example would be a list type.  Each concrete instance of a list, such
as a list-of-integers or list-of-strings, is a distinct monotype.  Since it is,
in principle, possible to build a list of anything, a function operating over
any sort of list is polymorphic.

`Type Classes`
--------------

`Type Classes`_ provide an ad-hoc polymorphism that chooses function
implementations based on the type of argument(s) provided.  In the simplest
cases, type classes provide a capability similar to function overloading.  A
type class defines a set of functions, i.e., an interface, that may be applied
to arguments of a variety of types.  To use an arbitrary type as a instance of
the type class, a programmer implements the interface for that type.  To see
this in more concrete terms, consider a Type Class `Hashable` that defines a
single function `hash`.  This function takes an arbitrary argument and returns
an integer representing its hash.  A programmer wishing to hash a particular
type, say a list of integers, first provides an instance declaration that
implements `hash` for lists of integers.  Instances can be provided for any
number of types, and it is the compiler's job to decide which version to use in
any particular case.

.. _Hindley-Milner Type System: https://en.wikipedia.org/wiki/Hindley%E2%80%93Milner_type_system
.. _Type Classes: https://en.wikipedia.org/wiki/Type_class
