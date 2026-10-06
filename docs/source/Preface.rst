=======
Preface
=======

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

.. _important-notes:

Important Notes
===============

[1] Type signatures are optional for goals.
    Sprite reads the type of every function and constructor from the
    interface that the Curry front end writes beside a module.  A goal
    without a type signature keeps its class constraints, and Sprite
    defaults them as the REPL of PAKCS does: ``Num`` to ``Int``,
    ``Fractional`` to ``Float``, ``Monad`` to ``IO``, a lone ``Data`` to
    ``Bool``.  A constraint outside that table, such as ``Enum a`` for
    ``toEnum 65``, is an error that asks for a type annotation.
    Expressions built in Python with :func:`curry.expr` are typed before
    they are built; see :ref:`typed-expressions`.


[2] The front end runs once per change.
    Sprite relies on an external program, the Curry front end of PAKCS, to
    convert Curry source code into FlatCurry, from which it writes an
    intermediate representation called ICurry.  The front end is the
    slowest step of the compilation: a fraction of a second for a small
    module (0.6 s for ``Peano``), seconds for a large one, and nothing when
    the files are current.  It does not affect the performance of programs
    compiled by Sprite.  On the C++ backend a module runs interpreted at
    once, and its compilation to native code happens in the background.


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
whose prior work deeply informed my understanding.


.. _Fair Scheme: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Curry: https://www.curry-lang.org/
.. _pull-tabbing: https://www.researchgate.net/publication/221323261_On_a_Tighter_Integration_of_Functional_and_Logic_Programming
