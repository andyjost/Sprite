=======
Preface
=======

This document describes the Sprite Curry system, developed by Andrew Jost.
Sprite is an implementation of the `Curry`_ programming language based on an
evaluation strategy called the `Fair Scheme`_, developed by Andrew Jost and
Sergio Antoy.  This is a `pull-tabbing`_ strategy that aims to avoid committing
to any step that would later need to be undone in a complete search.

Sprite consists of tools and Python libraries that provide everything one needs
to compile and execute Curry programs.  Programs can be compiled and run in
batch mode from the command mode or through a Python API.  The Python API is
considered a major contribution of this work, as it greatly simplifies the
integration of Functional-Logic Programming into other environments.


Important Note
==============

Sprite relies on an external program available from the `Curry Package
Manager`_ to convert Curry source code into an intermediate representation
called `ICurry`_.  This is typically the slowest step by far in the compilation
process, requiring several seconds for trivial programs.  Although this may
limit the pracicality of Sprite in certain situations, it does not affect the
performance of programs compiled by Sprite.


Acknowledgements
================

This work has been supported by NSF grant #1317249.  Many thanks to Sergio
Antoy for guiding me through the world of Functional-Logic Programming, helping
to develop the Fair Scheme, and much more.  Without his help, this work would
not have been possible.  Thanks also go to the many people who developed and
supported PAKCS and KiCS2, but especially Michael Hanus for important bug fixes
and improvements.

.. _Fair Scheme: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _pull-tabbing: https://www.researchgate.net/publication/221323261_On_a_Tighter_Integration_of_Functional_and_Logic_Programming
.. _Curry Package Manager: https://www-ps.informatik.uni-kiel.de/currywiki/tools/cpm
.. _ICurry: https://web.cecs.pdx.edu/~antoy/homepage/publications/wflp19/paper.pdf
