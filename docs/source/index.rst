.. title:: Sprite

======
Sprite
======

Sprite compiles and runs `Curry`_, and lets you call it from Python. Curry is
a functional logic programming language. Its functional half is Haskell's,
syntax included: algebraic data types, pattern matching, type inference, lazy
evaluation. Its logic half adds nondeterminism, logic variables and search: a
function may have several results, a value may be left unknown, and the
runtime finds the values that fit by unification. So you can state what a
result has to satisfy and leave the search to the language. Sprite's
evaluation strategy, the Fair Scheme, is proved correct and optimal: it finds
exactly the values of an expression, and it executes only the steps needed to
produce them. The strategy and its proofs are written up in a `dissertation`_
and a shorter `paper`_.

Sprite is in alpha. Try it, and tell us what breaks on the `issue tracker`_.

A first module
==============

Here is a Curry module. It defines a small type of Boolean formulas and a
function that prints one.

.. code-block:: haskell

   -- Logic.curry
   data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

   render :: Formula -> String
   render T = "T"
   render F = "F"
   render (Not p) = "!" ++ render p
   render (And p q) = "(" ++ render p ++ "&" ++ render q ++ ")"
   render (Or p q) = "(" ++ render p ++ "|" ++ render q ++ ")"

If you've read Haskell, nothing here is new. Save it next to your Python
code and import it:

.. code-block:: python

   import curry
   curry.path.insert(0, '.')
   from curry.lib import Logic as L

   f = L.And(L.Or(L.T, L.F), L.Not(L.F))
   goal = L.render(f)
   curry.eval(goal).one()    # '((T|F)&!F)'

The constructors of ``Formula`` are there as ``L.T``, ``L.And`` and so on,
and the result comes back as a Python string. ``L.render(f)`` builds an
expression without running it; ``curry.eval`` runs it, and ``.one()``
returns its value when there is exactly one. The first import translates
and compiles the module; later imports reuse the result.

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
.. _dissertation: https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf
.. _paper: http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry homepage: https://www.curry-lang.org/
.. _live demo: https://smap.curry-lang.org/smap.cgi?new/curry
.. _issue tracker: https://github.com/andyjost/Sprite/issues
