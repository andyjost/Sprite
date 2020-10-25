Overview
========
This file describes the metadata used in ICurry for the Python target.  These
are Python-specific annotations applied to ICurry, which are used to implement
built-ins, system facilities, and other special features.  The metadata is
supplied when declaring ICurry bindings for hand-implemented symbols (see
prelude.py).



IConstructor Metadata
=====================

Metadata: py.format
-------------------
Overrides the default show function.  The value may either be a string, which
will be formatted with the successor representations, or a function, which will
be called with the successors.

One use of this is to provide special formatting for lists and tuples.


Metadata: py.tag
----------------
Used for special node types, such as failures and choices, to indicate their
type.



IFunction Metadata
==================

Function metadata is used to bind builtin Curry functions to the Python
functions that implement them.


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

The value is a Python function that takes an interpreter followed by an
arbitrary number of positional node arguments.  The node arguments will be
head-normalized before being passed to the function, but no other preprocessing
(e.g., unboxing) is done.  The function is required to return a sequence of
arguments suitable for passing to Node.rewrite.

One use of this is to implement the "error" function.  If normalizing the
argument produces a special value (e.g., a function or choice), then Sprite
should apply the Fair Scheme normally.  When and if a head-normal value is
obtained (in this case, the next character of an error string) the given Python
function is called.

See compile_builtin.


Metadata: py.rawfunc
--------------------
Specifies a regular Python function that implements a Curry built-in.

The value is a Python function that takes an interpreter and the root node, of
the expression to rewrite.  The system will not do anything before calling that
function.  In particular, the successors will not be head-normalized, so it is
up to the implementation function to do that, if necessary.  

One use of this is to implement the =:= operator, which needs to work directly
with unbound free variables.

See compile_rawfunc.

