Overview
========
This file describes the metadata used when translating ICurry.  The optional
prefix restricts which backend the metadata is targeted to.  'all' means the
metadata applies to all backends.  The ones beginning with 'py' are
Python-specific annotations, which are used to implement built-ins, system
facilities, and other special features.  The metadata is supplied when
declaring ICurry bindings for hand-implemented symbols (see prelude.py).


IConstructor Metadata
=====================

Metadata: all.flags
-------------------
See InfoTable.  Used to flag certain built-in types that requre special
handling during formatting and other operations.


Metadata: py.format
-------------------
Overrides the default show function.  The value may either be a string, which
will be formatted with the successor representations, or a function, which will
be called with the successors.

One use of this is to provide special formatting for lists and tuples.


Metadata: all.tag
----------------
Used for special node types, such as failures and choices, to indicate their
type.


IFunction Metadata
==================

Function metadata is used to bind builtin Curry functions to the Python
functions that implement them.


Metadata: py.boxedfunc
----------------------
Specifies a Python function over boxed values that implements a Curry
built-in.

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

See the compiler.synthesis module.


Metadata: all.monadic
---------------------
Indicates a monadic primitive.  Non-determinism in such functions is trapped
and raised as a runtime error.


Metadata: py.rawfunc
--------------------
Specifies a regular Python function that implements a Curry built-in.

The value is a Python function that takes an interpreter and the root node, of
the expression to rewrite.  The system will not do anything before calling that
function.  In particular, the successors will not be head-normalized, so it is
up to the implementation function to do that, if necessary.  

One use of this is to implement the =:= operator, which needs to work directly
with unbound free variables.

See the compiler.synthesis module.


Metadata: py.unboxedfunc
------------------------
Specifies a Python function over unboxed values that implements a Curry
built-in.

The supplied Python function is an ordinary function over the built-in types.
Examples are operator.add, math.cos, or chr.  This adaptor normalizes and
unboxes each argument, applies the Python function, and then rewrites the head
to the boxed result.

Such a function is adapted to Curry as follows:

  - Head-normalize and then unbox each argument.
  - Invoke py.unboxedfunc with the arguments prepared in the previous step.
  - Rewrite the LHS to be a boxed value of the type computed in the first
    step, with the value returned from py.boxedfunc.  The implementation function
    must return a scalar that can be interpreted as the appropriate type in
    Curry.

The argument and result types can be specified by setting the metadata to a
triple containing the function, argument type name, and result type name in
that order.  Each type name should be one of 'Int', 'Char', or 'Float'.  By
default, the argument type name is deduced by matching each datatype against
the function name.  So, 'plusInt' is assumed to be a function over integers.
The result type name is by default assumed to equal that of the arguments
unless the function name begins with 'eq', 'le', 'prim_eq', or 'prim_le', in
which case it is assumed to return a Boolean

See the compiler.synthesis module.
