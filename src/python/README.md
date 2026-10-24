Overview
========
This file describes the metadata used when translating ICurry.  The optional
prefix names its target: 'all' for shared metadata, 'cxx' for the C++ runtime.
The metadata is supplied when declaring ICurry bindings for built-in symbols.


IConstructor Metadata
=====================

Metadata: all.flags
-------------------
See InfoTable.  Used to flag certain built-in types that requre special
handling during formatting and other operations.



Metadata: all.tag
----------------
Used for special node types, such as failures and choices, to indicate their
type.


IFunction Metadata
==================

Function metadata describes built-in Curry functions.



Metadata: all.monadic
---------------------
Indicates a monadic primitive.  Non-determinism in such functions is trapped
and raised as a runtime error.
