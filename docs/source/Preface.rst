=======
Preface
=======

This document describes the Sprite Curry system, developed by Andrew Jost.
Sprite is an implementation of the `Curry`_ programming language based on an
evaluation strategy called the `Fair Scheme`_, developed by Sergio Antoy and
Andrew Jost.  This is a `pull-tabbing`_ strategy that aims to avoid committing
to any step that would later need to be undone in a complete search.

Sprite provides everything one needs to compile and execute Curry programs.
This can be done in batch using command-line tools or through a Python API.
The Python API is considered a major contribution of this work, as it greatly
simplifies the integration of Functional-Logic Programming into imperative
environments.


Important Note
==============

Sprite relies on an external program to convert Curry source code into an
intermediate representation called ICurry.  This is typically the slowest step
by far in the compilation process, requiring several seconds even for trivial
programs.  Although this greatly affects compilation times, it does not affect
the performance of programs compiled by Sprite.


Acknowledgements
================

This work has been supported by NSF grant #1317249.  My deepest gratitude goes
to Sergio Antoy for guiding me through the world of Functional-Logic
Programming, helping to develop the Fair Scheme, and much more.  Without his
patient effort, this work would not have been possible.  Thanks also go to the
many people who developed and supported PAKCS and KiCS2, but especially Michael
Hanus for important bug fixes and improvements, and Bernd Brassel whose
prior work deeply influenced my thinking.


.. _Fair Scheme: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _pull-tabbing: https://www.researchgate.net/publication/221323261_On_a_Tighter_Integration_of_Functional_and_Logic_Programming
