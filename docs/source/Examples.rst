========
Examples
========

Stage Sprite with ``make stage``, then run ``./run`` in a numbered
subdirectory of ``examples/``.  Each has a README, a run script and an
``expected.out`` recording stdout.  The first run also compiles the Curry
sources.  Scripts use the staged installation or ``SPRITE_HOME`` and the
flags of ``SPRITE_INTERPRETER_FLAGS``.

Start with :doc:`Quickstart` for lessons 01 and 02 in five minutes, then
:doc:`PythonAPI/UsingTheAPI` for the boundary in teaching order.  The tour
below is followed by applications, an optional specialist series and the
build-system capstone.  The README beside each script gives its scope and
limits; ``tests/unit_examples.py`` checks the recorded output.

Examples 03, 09, 11, 12, 22 and 25 are tested on C++ only: 03 shows generated
C++, 09 requires the stream channel, and the other searches exceed the
reference backend's practical budget.  Example 03 adds ``interpret:off``
so its internal section reads compiled code.  Example 04 saves and loads
objects and runs a saved program on C++ as well.

Tour: 00 to 09
==============

.. _example-00:

00: Curry at the command line
-----------------------------

``examples/00-run-curry-programs`` — Run a call-time choice by file, module or
goal with ``sprite-exec``.

.. _example-01:

01: Hello, both ways
--------------------

``examples/01-run-with-python`` — Send Python data to Curry, consume answers
and correct three boundary mistakes.

.. _example-02:

02: Compile and parse
---------------------

``examples/02-dynamic-code-generation`` — Compile a Nat module from text and
build goals with symbol calls and parse.

.. _example-03:

03: Metadata
------------

``examples/03-inspect`` — Read public module, symbol and type metadata before
an explicitly internal view of compiler products.

.. _example-04:

04: Session
-----------

``examples/04-static-compile`` — Compile, reload, recognize stale terms,
reset, save, load and wait for background compilation.

.. _example-05:

05: Trees
---------

``examples/05-trees`` — Construct and match trees on either side of the
boundary, then generate bounded shapes and a seeded tree.

.. _example-06:

06: Variables
-------------

``examples/06-variables`` — Read named bindings from narrowing, then observe
arithmetic suspension and resumption.

.. _example-07:

07: Choices, sharing, functions
-------------------------------

``examples/07-choices`` — Compare shared and independent choices, observe a
cyclic list and reuse a returned function.

.. _example-08:

08: Permutation sort
--------------------

``examples/08-permutation-sort`` — Generate permutations, keep sorted ones and
collect a multiset with a set function.

.. _example-09:

09: Streams
-----------

``examples/09-streams`` — Pull finite output, a prime prefix and running
totals from Curry I/O actions.


Applications: 10 to 19 and 25
=============================

.. _example-10:

10: N queens
------------

``examples/10-queens-set-functions`` — Use a set function to reject unsafe
permutations and draw a solution.

.. _example-11:

11: Sudoku
----------

``examples/11-sudoku`` — Fill the most constrained cell first so dead branches
fail early.

.. _example-12:

12: SEND + MORE = MONEY
-----------------------

``examples/12-cryptarithm`` — Use structural permutations and lazy column
checks to prune digit assignments.

.. _example-13:

13: Regular expressions
-----------------------

``examples/13-regex-nondeterminism`` — Generate words as nondeterministic
values and match by unification.

.. _example-14:

14: Expression parser
---------------------

``examples/14-parser-functional-patterns`` — Split input with functional
patterns and let failure prune parses.

.. _example-15:

15: Dependency solver
---------------------

``examples/15-dependency-solver`` — Search Python package data, pin a
preferred plan and explain a failed resolution.

.. _example-16:

16: Scheduling
--------------

``examples/16-scheduling`` — Constrain task start times with guards and
minimize the resulting makespan.

.. _example-17:

17: Type inference
------------------

``examples/17-type-inference`` — Treat unknown types as free variables and
infer them by unification.

.. _example-18:

18: Text extraction
-------------------

``examples/18-text-extraction`` — Compile extraction rules at run time and
aggregate their answers in Python.

.. _example-19:

19: Blocks World application
----------------------------

``examples/19-blocks-world-app`` — Search by iterative deepening behind a
command line and an HTTP form, succeeding the retired Flask example.

.. _example-25:

25: Perfect hash
----------------

``examples/25-perfect-hash`` — Search programs by length for a Java-keyword
hash beside Python brute force over the same space.


Optional C++ type series: 20 to 23
==================================

.. _example-20:

20: C++ template deduction
--------------------------

``examples/20-cxx-types-deduction`` — Deduce template parameters by
unification and ask the inverse question over bounded types.

.. _example-21:

21: C++ overload resolution
---------------------------

``examples/21-cxx-types-overloads`` — Collect viable conversions and search
for argument types that make a call ambiguous.

.. _example-22:

22: C++ trait checking
----------------------

``examples/22-cxx-types-trait-check`` — Collect counterexamples to a trait
within a bounded type universe.

.. _example-23:

23: C++ member layout
---------------------

``examples/23-cxx-types-layout`` — Search member orders for a smaller layout
under an extra ordering constraint.


Capstone: 24
============

.. _example-24:

24: A makefile in Curry
-----------------------

``examples/24-build-system`` — Query a build relation in several directions
while Python owns timestamps and recipe execution.

Support sources
===============

``examples/cxx/`` contains the modules shared by 20 to 23;
``examples/Peano.curry`` supplies the metadata fixture of 03.  These support
sources have no separate run script or expected-output test.  Lesson 02
contains the Nat introduction.
