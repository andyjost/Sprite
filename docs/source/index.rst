.. title:: Sprite

======
Sprite
======

Sprite is an implementation of the multi-paradigm programming language
`Curry`_ exposed to Python. It seamlessly integrates features of functional
programming (algebraic data types, pattern matching, strong typing, type
inference, lazy evaluation) and logic programming (nondeterminism, logic
variables, search) into your Python project without adding heavy dependencies.
You state what a desired value has to satisfy and leave the search to Sprite.
As a result, many programs are trivial to construct and obviously correct.
Sprite's evaluation strategy, the Fair Scheme, is proved sound, complete, and
optimal, meaning it finds exactly the values of any expression, and it
executes only the steps needed to produce them. The strategy and its proofs
are written up in a `dissertation`_ and a shorter `paper`_.

Curry imports directly into Python. Your project uses it at whatever granularity
it chooses, freely mixing imperative, functional, and logic styles. In other
words, you always get to use the best tool exactly where it makes sense.

Curry code can be compiled ahead of time, :doc:`embedded in an application
<PythonAPI/UsingTheAPI>` as a saved object or program, interpreted where no
compiler is installed, or compiled just in time. You choose per deployment; the
evaluation is the same in each.

Sprite is in alpha. Install it with ``pip install --pre curry``. Try it and
tell us what breaks on the `issue tracker`_.

Getting started
===============

The following Curry module defines a small type of Boolean formulas along with
a printer.

.. code-block:: haskell

   -- Logic.curry
   data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

   render :: Formula -> String
   render T = "T"
   render F = "F"
   render (Not p) = "!" ++ render p
   render (And p q) = "(" ++ render p ++ " & " ++ render q ++ ")"
   render (Or p q) = "(" ++ render p ++ " | " ++ render q ++ ")"

So far this is ordinary Haskell code. Save it next to your Python code, then
import it, construct a formula, and render it as a string:

.. code-block:: python

   import curry
   curry.path.insert(0, '.')          # Curry's sys.path
   from curry.lib import Logic as L   # compiles and imports ./Logic.curry

   formula = L.And(L.Or(L.T, L.F), L.Not(L.F))
   goal = L.render(formula)
   curry.eval(goal).one()             # the one value: '((T | F) & !F)'

The import compiles the Curry module to native code and loads it. The
constructors of ``Formula`` appear as ``L.T``, ``L.And``, and so on.
``L.render(formula)`` builds an expression without running it, ``curry.eval``
evaluates it, and Sprite converts the result to a Python string.

Where to go next
================

- :doc:`Installation/Installation` installs Sprite with pip, or from
  source.
- The :doc:`Quickstart` takes the next steps.  The
  :doc:`Examples` are the tutorial: twenty-six programs, from a first
  Curry program to applications.
- The :doc:`CurryPrimer/index` teaches the language to a Python
  programmer.
- :doc:`Status` says what Sprite is today.

For Curry researchers: Sprite uses the Curry front end of PAKCS and ships
the ``base`` library of PAKCS 3.10.0, so most programs written for PAKCS
run unchanged; :doc:`Status` lists what differs.  The `Curry homepage`_
has the tutorial and the report of the language, and the `live demo`_
runs Curry in a browser.

.. toctree::
   :maxdepth: 1
   :caption: Getting started

   Installation/Installation
   Quickstart
   Examples
   CurryPrimer/index

.. toctree::
   :maxdepth: 1
   :caption: User guide

   PythonAPI/index
   REPL
   CommandLineInterface/index
   Introduction/Introduction

.. toctree::
   :maxdepth: 1
   :caption: Reference

   Reference/index
   Performance
   Status
   Installation/SoftwareCompatibility
   genindex

.. toctree::
   :maxdepth: 1
   :caption: Project

   DeveloperSetup
   DeveloperNotes
   Introduction/ProjectLayout
   Contributing
   Support
   License
   ReleaseNotes
   Preface

.. _Curry: https://www.curry-lang.org/
.. _dissertation: https://doi.org/10.15760/etd.3564
.. _paper: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry homepage: https://www.curry-lang.org/
.. _live demo: https://smap.curry-lang.org/smap.cgi?new/curry
.. _issue tracker: https://github.com/andyjost/Sprite/issues
