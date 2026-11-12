.. title:: Sprite

======
Sprite
======

Sprite is an implementation of the multi-paradigm programming language
`Curry`_, embedded in Python. It seamlessly integrates features of functional
programming and logic programming into your Python project. These features
include algebraic data types, pattern matching, strong typing, type inference,
lazy evaluation, nondeterminism, logic variables, and search. Curry follows
Haskell's syntax while adding its own semantics. Its only dependency is one
small package, the Curry front end.

The functional side rests on graph rewriting, the well-studied evaluation model
behind lazy languages such as Haskell. Here, a program is a set of rewrite
rules, applied lazily and only as far as a result demands. For the logic side,
you state what a desired value has to satisfy, leaving search to the runtime.
Many programs then read as their own specification, which keeps them simple,
short, and obviously correct. Sprite's evaluation strategy, the Fair Scheme, is
proved sound, complete, and optimal. This means it computes all and only the
values of any source expression, and every step it takes is one that any
strategy must take. The strategy and its proofs are written up in a
`dissertation`_ and a shorter `paper`_.

With Sprite, you don't have to write your whole project in a functional or
logic language, and deal with the integration and distribution issues that
entails. Write the part that is naturally a search or a set of rules as a small
Curry module, then simply import that module. The first import translates the
module and caches the result beside the source, without a C++ compiler. For
speed, the same code compiles to native machine code, either just in time as
the program runs (the ``jit`` extra) or ahead of time into an object you can
:doc:`embed in an application <PythonAPI/UsingTheAPI>`.

Sprite is in alpha. Install it with ``pip install --pre curry``. Try it and
tell us what breaks on the `issue tracker`_.

Getting started
===============

Here is a Curry module for Boolean formulas:

.. code-block:: haskell

   -- Logic.curry
   data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

   render :: Formula -> String
   render T = "T"
   render F = "F"
   render (Not p) = "!" ++ render p
   render (And p q) = "(" ++ render p ++ " & " ++ render q ++ ")"
   render (Or p q) = "(" ++ render p ++ " | " ++ render q ++ ")"

The module declares a data type, ``Formula``, with five constructors, and a
function, ``render``, over that type. This Curry snippet is also valid Haskell.
Save it next to your Python code, then import it, construct a formula, and
render it as a string:

.. code-block:: python

   import curry
   curry.path.insert(0, '.')          # Curry's sys.path
   from curry.lib import Logic as L   # compiles and imports ./Logic.curry

   formula = L.And(L.Or(L.T, L.F), L.Not(L.F))
   goal = L.render(formula)
   curry.eval(goal).one()             # the one value: '((T | F) & !F)'

The constructors of ``Formula`` and the ``render`` function appear as Python
objects. ``L.render(formula)`` builds an expression without running it;
``curry.eval`` evaluates it, and Sprite converts the result to a Python string.

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
run unchanged; :doc:`CommandLineInterface/sprite-exec` runs a program, the
:doc:`REPL <REPL>` opens a prompt and :doc:`Status` lists what differs.  The `Curry homepage`_
has the tutorial and the report of the language, and the `live demo`_
runs Curry in a browser.

.. toctree::
   :maxdepth: 1
   :caption: Getting started

   Installation/Installation
   Quickstart
   CurryInTenMinutes
   Examples
   CurryPrimer/index

.. toctree::
   :maxdepth: 1
   :caption: User guide

   PythonAPI/index
   CompilationOptions
   REPL
   CommandLineInterface/index

.. toctree::
   :maxdepth: 1
   :caption: Reference

   Reference/index
   Performance
   Status
   Compatibility
   Installation/SoftwareCompatibility
   genindex

.. toctree::
   :maxdepth: 1
   :caption: Project

   ReleaseNotes
   Support
   Contributing
   DeveloperSetup
   DeveloperNotes
   CompilationPipeline
   DevelopmentVariables
   Introduction/ProjectLayout
   License
   Acknowledgements

.. _Curry: https://www.curry-lang.org/
.. _dissertation: https://doi.org/10.15760/etd.3564
.. _paper: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry homepage: https://www.curry-lang.org/
.. _live demo: https://smap.curry-lang.org/smap.cgi?new/curry
.. _issue tracker: https://github.com/andyjost/Sprite/issues
