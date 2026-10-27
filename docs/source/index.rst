.. title:: Sprite

======
Sprite
======

**Sprite brings the Curry language to Python.** `Curry`_ is a functional
logic language.  It has the strongly typed functions and the lazy
evaluation of Haskell, and it adds two ideas from logic programming to the
language itself: a function may have several results, and a value may be
left unknown for the program to find.

Sprite compiles Curry modules to native code by way of C++ and runs them in
its own runtime, and its Python API imports a Curry module like a Python
module.  Underneath is the Fair Scheme, an evaluation strategy that has
been proved correct and complete: a computation finds every value of an
expression and nothing else, in whatever order the alternatives are
explored.  The strategy and its proofs are written up in a `dissertation`_
and a shorter `paper`_.

A first program
===============

The functions live in a Curry file, with their types:

.. code-block:: haskell

   -- Hello.curry
   greet :: String -> String
   greet name = "Hello, " ++ name ++ "!"

Python imports the module directly.  The first import translates it and
compiles it to native code in the background; every later import reuses
the result.

.. code-block:: python

   import curry
   curry.path.insert(0, '.')      # the directories where Curry modules are found
   from curry.lib import Hello

   goal = Hello.greet('World')    # a Curry expression, typed from the signature
   curry.eval(goal).one()         # evaluate it and take its one value
   # 'Hello, World!'

Where to go next
================

- :doc:`Installation/Installation` installs Sprite with pip, or from
  source.
- The :doc:`Quickstart` continues from the program above.  The
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
