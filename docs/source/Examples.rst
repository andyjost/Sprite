========
Examples
========

The ``examples/`` directory of the repository holds runnable examples.  Each
example has a README, a run script, and a file ``expected.out`` with the exact
output of the run script.  Most examples have a Python driver, ``go.py``, and
one Curry module.

To run an example, stage Sprite with ``make stage`` and run the script from
the example directory:

.. code-block:: bash

    cd examples/10-queens-set-functions
    ./run

A run script uses the C++ backend by default.  The scripts of examples 03
and 04 set the Python backend, because those examples run on it only:
example 03 prints the generated Python of a function, and example 04 saves
a module in the Python form.  To pick a backend for the others, set
``SPRITE_INTERPRETER_FLAGS`` in the environment:

.. code-block:: bash

    SPRITE_INTERPRETER_FLAGS=backend:py ./run

The first run of an example also runs the Curry front end on its module.
That takes a fraction of a second per module: example 01 took 0.56 s on
its first run and 0.15 s on the second, on the machine of this text.  The
test ``tests/unit_examples.py`` runs every example on the backends it
declares and compares the output with ``expected.out``; the backends named
below are the ones of that test.

The sections below name each example, its backends, and its idea, and quote
its README.

Run Curry programs with sprite-exec
===================================

Directory ``examples/00-run-curry-programs``.  Backends: Python, C++.

One program runs three ways: by file name, by module name, and with another goal.  Its two goals show call-time choice: a shared choice gives two values, two independent choices give four.

.. code-block:: bash

    cd examples/00-run-curry-programs
    ./run

.. literalinclude:: ../../examples/00-run-curry-programs/README
   :language: text

Run a Curry program from Python
===============================

Directory ``examples/01-run-with-python``.  Backends: Python, C++.

The first contact with the Python API.  A script imports a Curry module from its own directory and prints every value of a goal.

.. code-block:: bash

    cd examples/01-run-with-python
    ./run

.. literalinclude:: ../../examples/01-run-with-python/README
   :language: text

Compile Curry code at run time
==============================

Directory ``examples/02-dynamic-code-generation``.  Backends: Python, C++.

A Python program compiles a Curry module from a string and builds two goals, one with ``curry.expr`` and one with ``curry.compile``.  Each compile runs the Curry front end.

.. code-block:: bash

    cd examples/02-dynamic-code-generation
    ./run

.. literalinclude:: ../../examples/02-dynamic-code-generation/README
   :language: text

Inspect Curry objects from Python
=================================

Directory ``examples/03-inspect``.  Backends: Python.

The module ``curry.inspect`` lists the symbols and the types of a loaded module and finds its ICurry files.  The example also prints the Python code that Sprite generated for one function.

.. code-block:: bash

    cd examples/03-inspect
    ./run

.. literalinclude:: ../../examples/03-inspect/README
   :language: text

Compile a Curry module to a Python script
=========================================

Directory ``examples/04-static-compile``.  Backends: Python.

``curry.save`` writes the compiled module to a Python script with a goal, and the script runs the goal.

.. code-block:: bash

    cd examples/04-static-compile
    ./run

.. literalinclude:: ../../examples/04-static-compile/README
   :language: text

N queens with set functions
===========================

Directory ``examples/10-queens-set-functions``.  Backends: Python, C++.

A non-deterministic permutation, a functional pattern, and a set function solve the puzzle in four functions.  Python counts the solutions of each board size and draws the smallest one.

.. code-block:: bash

    cd examples/10-queens-set-functions
    ./run

.. literalinclude:: ../../examples/10-queens-set-functions/README
   :language: text

Sudoku by search
================

Directory ``examples/11-sudoku``.  Backends: C++.

The search is the program: a choice fills the most constrained cell, and a branch dies when a cell has no candidate.  Python reads the grids, counts the solutions, and prints them.

.. code-block:: bash

    cd examples/11-sudoku
    ./run

.. literalinclude:: ../../examples/11-sudoku/README
   :language: text

Cryptarithms: SEND + MORE = MONEY
=================================

Directory ``examples/12-cryptarithm``.  Backends: C++.

A structural permutation of the digits and a guard that checks the columns from the units column upward solve any cryptarithm.  Python validates the words and prints the completed sums.

.. code-block:: bash

    cd examples/12-cryptarithm
    ./run

.. literalinclude:: ../../examples/12-cryptarithm/README
   :language: text

Regular expressions by non-determinism
======================================

Directory ``examples/13-regex-nondeterminism``.  Backends: Python, C++.

A function returns one word of the language of a pattern, and every word is one value, so the function generates the words; matching is unification with the subject.  Python parses the pattern syntax into Curry data, lists the words of a star-free pattern, and lists every hit of a search.

.. code-block:: bash

    cd examples/13-regex-nondeterminism
    ./run

.. literalinclude:: ../../examples/13-regex-nondeterminism/README
   :language: text

An expression parser from functional patterns
=============================================

Directory ``examples/14-parser-functional-patterns``.  Backends: Python, C++.

Functional patterns split the input around an operator, and a split whose parts do not parse fails.  Python prints the parse tree and the value of each expression.

.. code-block:: bash

    cd examples/14-parser-functional-patterns
    ./run

.. literalinclude:: ../../examples/14-parser-functional-patterns/README
   :language: text

A package dependency solver
===========================

Directory ``examples/15-dependency-solver``.  Backends: Python, C++.

A plan picks a version for every package that the roots reach, and a search over the candidates, newest first, finds the consistent plans.  A set function pins the preferred plan, and a failure is explained.  The index is nested Python data, and the output is a lockfile.

.. code-block:: bash

    cd examples/15-dependency-solver
    ./run

.. literalinclude:: ../../examples/15-dependency-solver/README
   :language: text

Scheduling tasks fed from Python data
=====================================

Directory ``examples/16-scheduling``.  Backends: Python, C++.

Each task gets a start slot by a choice, and guards forbid overlap and enforce precedences.  Python grows the horizon until a schedule exists and draws a Gantt chart.

.. code-block:: bash

    cd examples/16-scheduling
    ./run

.. literalinclude:: ../../examples/16-scheduling/README
   :language: text

Type inference by unification
=============================

Directory ``examples/17-type-inference``.  Backends: Python, C++.

Free variables are unknown types and ``=:=`` is unification.  Python builds lambda terms, and an ill-typed term has no value.

.. code-block:: bash

    cd examples/17-type-inference
    ./run

.. literalinclude:: ../../examples/17-type-inference/README
   :language: text

Text extraction with functional patterns, compiled at run time
==============================================================

Directory ``examples/18-text-extraction``.  Backends: Python, C++.

Extraction rules are Curry text inside the Python program, compiled once with ``curry.compile``.  Curry extracts the fields and tags of each line, and Python aggregates them.

.. code-block:: bash

    cd examples/18-text-extraction
    ./run

.. literalinclude:: ../../examples/18-text-extraction/README
   :language: text

Blocks World as a command-line application
==========================================

Directory ``examples/19-blocks-world-app``.  Backends: Python, C++.

A non-deterministic move and a bounded search give a shortest plan by iterative deepening.  An argparse front end parses the worlds and draws the plan, and an optional form uses ``http.server``.

.. code-block:: bash

    cd examples/19-blocks-world-app
    ./run

.. literalinclude:: ../../examples/19-blocks-world-app/README
   :language: text

C++ compile time
================

The examples 20 to 23 form a series.  They model the compile-time algorithms
of a C++ compiler over one algebraic model of C++ types, the shared Curry
modules under ``examples/cxx``: template argument deduction and the partial
ordering of specializations, overload resolution, trait checking, and member
layout.  A template parameter is a Curry free variable, search is
non-determinism, and set functions collect the results.  The motivation is a
future integration with the Circle C++ compiler, whose compile-time
metaprogramming can run Python; Sprite would supply the search and the
unification, and Circle the types.  The model is a simplification of the C++
type system, and each README says what it leaves out.  The README of example
20 introduces the series.

Template argument deduction over a model of C++ types
-----------------------------------------------------

Directory ``examples/20-cxx-types-deduction``.  Backends: Python, C++.

A template parameter is a free variable, and deduction is unification of the parameter pattern with the argument type.  A set function turns a failed deduction into an empty set, and the partial ordering of specializations is deduction again.  Python builds the C++ types and prints the answers.

.. code-block:: bash

    cd examples/20-cxx-types-deduction
    ./run

.. literalinclude:: ../../examples/20-cxx-types-deduction/README
   :language: text

Overload resolution over a model of C++ types
---------------------------------------------

Directory ``examples/21-cxx-types-overloads``.  Backends: Python, C++.

The conversions of the standard are non-deterministic rules, a candidate with an argument that no rule converts is not viable, and a set function collects the viable set with its ranks.  The inverse question finds every argument type up to a depth that makes a call ambiguous.  Python builds the overload sets, the class hierarchy and the calls.

.. code-block:: bash

    cd examples/21-cxx-types-overloads
    ./run

.. literalinclude:: ../../examples/21-cxx-types-overloads/README
   :language: text

Trait checking by narrowing over a model of C++ types
-----------------------------------------------------

Directory ``examples/22-cxx-types-trait-check``.  Backends: C++.

A bounded generator enumerates every well-formed type of the model up to a depth, one per value, and narrowing with ``=:=`` binds an unknown type to each.  A set function collects the types for which a property of a trait is False, so an empty set is the verdict that the property holds.  One trait is wrong on purpose, and the search finds every counterexample.

.. code-block:: bash

    cd examples/22-cxx-types-trait-check
    ./run

.. literalinclude:: ../../examples/22-cxx-types-trait-check/README
   :language: text

Member layout by search over a model of C++ types
-------------------------------------------------

Directory ``examples/23-cxx-types-layout``.  Backends: Python, C++.

A non-deterministic permutation yields every order of the members of a struct, a set function collects the size of each order, and a constraint on the order is one more guard.  Python describes the struct through the annotations of a class, as a reflection would, and prints the layout tables.

.. code-block:: bash

    cd examples/23-cxx-types-layout
    ./run

.. literalinclude:: ../../examples/23-cxx-types-layout/README
   :language: text

A makefile in Curry
-------------------

Directory ``examples/24-build-system``.  Backends: Python, C++.

The makefile of a toy C project is a Curry module beside its sources: the variables are definitions, the pattern rule ``%.o: %.c`` is an equation with a functional pattern, and a rule is a value.  The library ``Make.curry`` reads the makefile through a set function and answers the questions of make over it: what a target reads, what is stale over a table of stamps, the plan in waves, the targets that can run now, the targets a change touches, the targets that two rules claim, and the sources that are missing.  The driver ``make.py``, generic for a C project, owns the world: it scans the includes, reads the stamps, runs the commands in a thread pool, and asks Curry for the ready set after each completion.  Nothing in Python names a file of the project.

.. code-block:: bash

    cd examples/24-build-system
    ./run

.. literalinclude:: ../../examples/24-build-system/README
   :language: text
