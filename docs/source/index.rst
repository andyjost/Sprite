.. title:: Sprite

======
Sprite
======

Sprite puts a logic engine in your Python program. You write what an answer
has to satisfy, as ordinary typed code, and the runtime finds it. Write a
printer and the parser comes with it. Write the rule for a dependency once
and ask it in either direction. The language is `Curry`_: it looks like
Haskell, and it adds nondeterminism, logic variables and search to the
language itself. Sprite compiles Curry to native code and imports it like a
Python module. Underneath is the Fair Scheme, an evaluation strategy proved
sound, complete and optimal; the strategy and its proofs are written up in a
`dissertation`_ and a shorter `paper`_.

Sprite is in alpha. ``pip install --pre curry`` brings two small wheels and
nothing else. Try it, and tell us what breaks on the `issue tracker`_.

The printer and the parser
==========================

Say you have a data type and a function that prints it. One day you need
the text back as data, for a round trip or a config file. In Python you'd
write a tokenizer and a recursive-descent parser, and keep them in step
with the printer by hand. In Curry it's one line, the last one in this
module:

.. code-block:: haskell

   -- Logic.curry
   data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

   render :: Formula -> String
   render T = "T"
   render F = "F"
   render (Not p) = "!" ++ render p
   render (And p q) = "(" ++ render p ++ " & " ++ render q ++ ")"
   render (Or p q) = "(" ++ render p ++ " | " ++ render q ++ ")"

   parse :: String -> Formula
   parse (render p) = p

The data type and ``render`` are plain functional code, as in Haskell. The
pattern of ``parse`` is where Curry departs: it's a call of ``render`` with
an unknown argument. To match it, Sprite solves for the formula ``p`` whose
rendering is the input, and that ``p`` is the result. From Python:

.. code-block:: python

   import curry
   curry.path.insert(0, '.')          # Curry's sys.path
   from curry.lib import Logic as L   # compiles and imports ./Logic.curry

   formula = L.And(L.Or(L.T, L.F), L.Not(L.F))
   goal = L.render(formula)
   text = curry.eval(goal).one()        # the one value: '((T | F) & !F)'
   tree = curry.eval(L.parse(text)).one()
   print(tree)                          # And (Or T F) (Not F)
   tree == formula                      # True
   list(curry.eval(L.parse('(T &')))    # []

That's the whole parser. There's no second copy of the grammar to keep in
step, and the parser can't disagree with the printer, because it is the
printer. Malformed input has no value, so the list comes back empty. This
is where Curry excels: the specification is the program, and there's
nothing more to write and nothing more to get wrong.

The Python side is as thin as it looks. ``curry.path`` is Curry's
``sys.path``; the first import compiled ``Logic.curry`` to native code, or
interprets it on a machine without a C++ compiler, and later imports reuse
the result; the constructors are there as ``L.And`` and friends; and the
string came back as a plain ``str``.

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
