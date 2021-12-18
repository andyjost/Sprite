=======
Preface
=======

This document describes the Sprite Curry system, developed by Andrew Jost.
Sprite is an implementation of the `Curry`_ programming language based on an
evaluation strategy called the `Fair Scheme`_, developed by Sergio Antoy and
Andrew Jost.  This is a `sequential` strategy that relies on `pull-tabbing`_ to
avoid taking irrevocable non-deterministic steps that could jeopardize the
competeness of computations.

Sprite provides everything one needs to compile and execute Curry programs.
This can be done in batch using command-line tools or through a Python API.
The Python API is considered a major contribution of this work, as it greatly
simplifies the integration of Functional-Logic Programming into imperative
environments.

.. _important-notes:

Important Notes
===============

[1] Supply type signatures for goals.
    Recent implementations of Curry support type classes.  Sprite is no
    different in this regard, but it currently does not have a type inferrence
    system.  This means that goals with no type signature might fail, as Sprite
    has no way to supply a default instance.


[2] Have patience when compiling.
    Sprite relies on an external program to convert Curry source code into an
    intermediate representation called ICurry.  This is typically the slowest
    step by far in the compilation process, requiring several seconds even for
    trivial programs.  Although this greatly affects compilation times, it does
    not affect the performance of programs compiled by Sprite.


Acknowledgements
================

This work has been supported by NSF grant #1317249.  My deepest gratitude goes
to Sergio Antoy for guiding me through the world of Functional-Logic
Programming, helping to develop the Fair Scheme, and much more.  Without his
patience and persistence, this work would not have been possible.  Thanks also
go to the many people who developed and supported PAKCS and KiCS2, but
especially Michael Hanus for his conscientious efforts to develop and
thoroughly document Curry, and his many useful suggestions, bug fixes, and
other improvements that affected my work.  Thanks also to Bernd Brassel, whose
prior work deeply informed my understanding.


.. _Fair Scheme: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _pull-tabbing: https://www.researchgate.net/publication/221323261_On_a_Tighter_Integration_of_Functional_and_Logic_Programming
