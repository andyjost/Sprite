============
About Sprite
============

This document describes the Sprite Curry system, developed by Andrew Jost.
Sprite is an implementation of the `Curry`_ programming language based on an
evaluation strategy called the `Fair Scheme`_, developed by Sergio Antoy and
Andrew Jost.  The Fair Scheme is a `sequential` strategy that relies on
`pull-tabbing`_ to avoid taking irrevocable non-deterministic steps that could
jeopardize the competeness of computations.

Sprite provides everything one needs to compile and execute Curry programs.
This can be done in batch using command-line tools or through a Python API.
The Python API is considered a major contribution of this work, as it greatly
simplifies the integration of Functional-Logic Programming into imperative
environments.

Acknowledgements
================

This work has been supported by NSF grant #1317249.  My deepest gratitude goes
to Sergio Antoy for guiding me through the world of Functional-Logic
Programming, helping to develop the Fair Scheme and ICurry, and much more.
Without his patience and persistence, or his passion to share his considerable
knowledge, this work would not have been remotely possible.  Special thanks go
to Michael Hanus, whose contributions to Curry and Function-Logic Programming
would be difficult to overstate.  His conscientious efforts to develop and
thoroughly document Curry over many years, plus his countless useful
suggestions, bug fixes, and other improvements (especially with respect to
ICurry) made this work possible.  Thanks also go to the many people who
developed and supported Curry, PAKCS and KiCS2, but particularly Bernd Brassel,
whose prior work deeply informed my understanding.  Malthe Borch held the
name ``curry`` on PyPI from 2009 for his package of partial application and
agreed to its transfer to this project; I am grateful for his generosity.


.. _Fair Scheme: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry: https://www.curry-lang.org/
.. _pull-tabbing: https://www.researchgate.net/publication/221323261_On_a_Tighter_Integration_of_Functional_and_Logic_Programming
