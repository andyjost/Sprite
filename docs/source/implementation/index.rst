Implementation
==============

.. toctree::

Computation
-----------

The computational state of a Curry program is stored in a *compute graph*.
This is a directed, possibly-cyclic graph.  Each node begins with a reference
to a compiler-generated data structure called the *info table* that provides
information such as the node label, type, and arity.  Following that is a
dynamic section, called the *data section*, whose size and layout are
determined by the node type.  This section may contain references to successor
nodes and literal (unboxed) data.

Nodes belong to one of six categories.  A slot of the info table called
the *tag* indicates which one.  The categories are:

  +------------+----------+-------------------------------+
  | tag        | value    | represents                    |
  +============+==========+===============================+
  |   FAIL     |  -6      | a failed computation          |
  +------------+----------+-------------------------------+
  |   CONSTR   |  -5      | a constraint                  |
  +------------+----------+-------------------------------+
  |   FREE     |  -4      | a free variable               |
  +------------+----------+-------------------------------+
  |   FWD      |  -3      | a forward reference           |
  +------------+----------+-------------------------------+
  |   CHOICE   |  -2      | a non-deterministic choice    |
  +------------+----------+-------------------------------+
  |   FUNC     |  -1      | a function                    |
  +------------+----------+-------------------------------+
  |   CTOR     |  >=0     | a constructor (see below)     |
  +------------+----------+-------------------------------+

Types in Curry are unions over constructor symbols.  For CTOR nodes, the tag
indicates which constructor is selected.  This is done by numbering the
constructors of each type in some fixed order starting from zero.


Constraints
-----------

A constraint is a special node that contains information about correlated
choices or free variables.  Constraints arise from certain applications of the
``=:=`` operator involving free variables.  Consider the following:

.. code-block:: haskell

    (x =:= True) &> x where x free

Evaluation of ``=:=`` produces a constraint object holding the information that
free variable ``x`` must be replaced with the value ``True``.  This information
is transmitted to another part of the computation, namely the right-hand side
of ``&>``, where it is needed to instantiate ``x``.

Constraint nodes contain two data elements.  The first is a reference to the
value of the constraint.  Since constraints belong to the runtime, not the
program being evaluated, they are always eliminated before a program value is
produced.  The constraint value is what is left behind after eliminating the
constraint.  In practice, since constraints eminate from applications of
``=:=``, the value is always a Boolean type.

The second is a description of the constraint.  Constraints come in three flavors:

  +-------------------+-----------------------------------------------------+
  | constraint flavor | purpose                                             |
  +===================+=====================================================+
  | EqVars            | constrain equivalent free variables                 |
  +-------------------+-----------------------------------------------------+
  | EqChoices         | constrain equivalent choices                        |
  +-------------------+-----------------------------------------------------+
  | ChoiceConstr      | constrain a choice to take the value LEFT or RIGHT  |
  +-------------------+-----------------------------------------------------+

Constraints are subject to pull-tabbing steps.  Upon reaching the top of an
expression they are added to an object called the *constraint store*.  Every
top-level evaluation context has one constraint store alongside its one
fingerprint.  The constraint store places constraints on the fingerprint.
Whenever a fingerprint found to be inconsistent with its constraint store, the
associated context becomes a failed computation.

Constraints can be thought of as unary objects.  Their only proper successor is
the value.  As such, and unlike choices, pull-tabbing a constraint does not
copy nodes or introduce any new branches in the compute graph.


Choices
-------



Free Variables
--------------

Free variables are implemented as singletons.  They are created explicitly by
``free`` clauses in Curry programs or implicitly through narrowing steps on
free variables.  Once created, a variable node is never copied or overwritten,
though it is possible to replace a reference to a variable within some context.

Like choices, free variables are assigned an integer, unique among free
variables, called the ``id``.  Choice and variable ids are taken from the same
pool and there is a special relationship between choices and variables with the
same id.  This will be discussed shortly.

Each free variable is associated with exactly zero or one generators.  A fresh
variable begins with no generator and is assigned one the first time it is
needed.  The generator for any type is defined as a choice among constructor
expressions, covering all its constructors, in which every argument to a
constructor is replaced with a fresh free variable.  The following code snippet
introduces a type and shows how the corresponding generator could be
constructed:

.. code-block:: haskell

    data TypeABC = A a1 a2 | B b1 | C
    gen_ABC = A x1 x2 ? B x3 ? C where x1, x2, x3 free

Free variables are replaced through a narrowing-like step called
*instantiation*.  When a variable is needed in context C, it is replaced with a
copy of its generator in C.  In the copy, choices are duplicated but free
variables are not (since they are singletons).  During the copying process, no
new choice or variable ids are allocated (the ids were assigned during
generator creation).  After instantiation, the Fair Scheme can process the
choices and produces all values in the usual way.

There are two additional contexts in which free variables might appear.  One is within
an application of ``=:=:``, such as the following:

.. code-block:: haskell

    x =:= True where x free

This expression is replaced with a constraint node.  The constraint value is
``True``, because the binding of ``x`` to ``True`` can succeed.  The constraint
description indicates how certain choices must be resolved to satisfy the
constraint.  Consider the following definition of the ``Bool`` generator:

.. code-block:: haskell

    gen_Bool = True ? False

Given this, the choice that appears in the generator of ``x`` must be resolved
"left."

The final context to consider is when a free variable is unneeded.  For example:

.. code-block:: haskell

    x::[Bool] where x free

In this case, reducing ``x`` to ground form is undesirable because it would
generate all possible lists of Boolean values.  There is an additional
consideration.  If the value of ``x`` is constrained within the constraint
store, then it may need to be (partially) instantiated.  Consider:

.. code-block:: haskell

    (x =:= [y]) &> x where x, y free

``x`` is unneeded in the same sense as in the previous example.  However,
application of ``=:=`` produces an entry in the constraint store pertinant to
``x``.  Let's assume the following generator for the List type:

.. code-block:: haskell

    gen_List = (:) x1 x2 ? [] where x1, x2 free

``x`` was constrained to be a non-empty list, therefore the choice appearing in
its generator is constrained "left."  Furthermore, since it was unified with
the expression ``[y]``, two further constraints were implicitly created:

.. code-block:: haskell

    x1 =:= y
    x2 =:= []

This information, all contained in the constraint store, must be considered
when producing a value for ``x`` in an unneeded context.

Fingerprints
------------

