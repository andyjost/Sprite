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

A run script uses the C++ backend by default unless the example runs on the
Python backend only.  To pick a backend, set ``SPRITE_INTERPRETER_FLAGS`` in
the environment:

.. code-block:: bash

    SPRITE_INTERPRETER_FLAGS=backend:py ./run

The first run of an example also compiles its Curry module, which takes about
10 s.  The test ``tests/unit_examples.py`` runs every example on the backends
it declares and compares the output with ``expected.out``.

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

``curry.save`` writes the compiled module to a Python script with a goal, and the script runs the goal.  The test suite lists this example as a known failure until ``curry.save`` is fixed.

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

A function returns one word of the language of a pattern, and every word is one value; matching is unification with the subject.  Python parses the pattern syntax into Curry data and lists every hit of a search.

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

A plan assigns each package one of its versions, and a guard keeps the consistent plans.  The package index is nested Python data, and Python picks the newest plan.

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
