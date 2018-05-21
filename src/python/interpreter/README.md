Overview
========
This file describes the metadata used in ICurry for the Python target.  These
are Python-specific annotations applied to ICurry, which are used to implement
built-ins, system facilities, and other special features.



IConstructor Metadata
=====================

Metadata: py.format
-------------------
Overrides the default show function.  The value may either be a string, which
will be formatted with the successor representations, or a function, which
will be called with the successors.


Metadata: py.tag
----------------
Used for special node types, such as failures and choices, to indicate their
type.



IFunction Metadata
==================

Metadata: py.primfunc
---------------------
Specifies a Python function to adapt into a Curry built-in.

This value is a Python function that behaves like an ordinary math function,
e.g., operator.add, or math.cos.

Such a function is adapted to Curry as follows:

  - Head-normalize and then unbox each argument.
  - Invoke py.primfunc with the arguments prepared in the previous step.
  - Rewrite the LHS to be a boxed value of the type computed in the first
    step, with the value returned from py.func.  The implementation function
    must return a scalar that can be interpreted as the appropriate type in
    Curry.

See compile_primitive_builtin.


Metadata: py.func
-----------------
Specifies a regular Python function that implements a Curry built-in.

The value is a Python function that takes an interpreter, followed by an
arbitrary number of positional node arguments.  The node arguments will be
head-normalized before being passed to the function, but no other preprocessing
(e.g., unboxing) is done.  The function is required to return a sequence of
arguments suitable for passing to Node.rewrite.

See compile_builtin.

