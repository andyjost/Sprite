Introduction
============

Sprite is a compiler and runtime for Curry programs.  It is based on the
`Fair Scheme`_, a compilation strategy for transforming declarative,
non-deterministic source programs into imperative, deterministic code.  The
Fair Scheme emphasizes operational completeness.  As such, Sprite aims to
produce all values of Curry programs, subject only to practical limits such as
the amount of memory available.

`Curry`_ is a Functional-Logic programming language with syntax based on
`Haskell`_.  Despite superficial similarities, Curry delivers a big
semantic punch, as it unifies disparate aspects of two of the foremost
programming paradigms.  From `Functional Programming`_ it acquires first-class,
higher-order, pure functions; strict (a.k.a., lazy) evaluation order; partial
application; immutable data; and pattern matching.  From `Logic Programming`_
it gains non-determinism, logic variables, and disjunctive control flow.

.. note::
  Learn about Curry at the `Curry Homepage`_.  The :ref:`curry-primer` gives a
  brief introduction intended to help orient unfamiliar readers.

The most salient of these are the Logic Programming features.  To a programmer
familiar with only Functional or Imperative Programming, they posses
preternatural qualities that are most foreign.  If one only describes an
object's properties, the runtime can deduce what it must be and conjure it at
runtime.  The execution state involves superpositions that somehow take on
multiple values at once.  Control flow is not linear or even localized to a
definite time or place; it rather branches out in exploratory fashion, as would
a parallel search.

These aspects hint at a tantalizing power that is somehow greater than what
Functional or Imperative languages seem to offer.  The potential to unlock this
has inspired `grand efforts
<https://en.wikipedia.org/wiki/Fifth_generation_computer>`__.

And yet.

Programming is often mundane.  It benefits not at all from an unfamiliar or
counter-intuitive way to skin the same cat.  One may not, for example, wish to
parse command-line arguments "preternaturally" or open a file by logical
inference, whatever that may mean in practice.  A `purely` Logic Programming
language, one could argue, is limited to the extent that it forces programmers
to do everything on its terms.

One might, therefore, regard Logic Programming as less practical than other
approaches.  And, indeed, if we estimate practicality as the number of
commercial products developed or the size of the user base, then the data
support this notion.  Not only that, but the utility of a programming language
must also be regarded as a function of the size and quality of its community,
libraries, and other resources, no matter what properties the language itself
may possess.  The question then arises of how one can make the most appealing
aspects of Logic Programming more palatable to more potential users.

Functional-Logic programming is a broad effort to synthesize aspects of
Functional and Logic Programming.  In light of the above, it can perhaps be
understood as an effort to couch Logic Programming in terms of more widely used
Functional programming languages.  Curry, in one sense, makes Logic Programming
more user-friendly by building on Haskell, with its well-developed community
and resources.  One can learn much of Curry by reading a Haskell tutorial.  And
one can write a mostly functional program that judiciously uses logic features
only where they make sense.

Sprite carries this idea to its logical conclusion.  By embedding Curry in
Python, Sprite allows one to choose between Functional, Imperative, and Logic
styles.  Each function, module, or other component of an application can choose
whichever is most appropriate for the task at hand.

In doing so Sprite meets programmers where they are.  Python is an enormously
popular language.  By packaging Functional-Logic programming as a Python
extension, it instantly becomes more approachable to a huge number of
programmers.  With Sprite, anyone can use Functional and Logic Programming
where it makes sense, while relying on Python where they prefer.

The remainder of this introduction gives a high-level overview of Sprite.  It
is intended to orient new users so that they may understand Sprite well enough
to begin using it.

.. toctree::
   :maxdepth: 1

   MajorFeatures
   ExternalSoftware
   ProjectLayout
   CompilationPipeline

.. _Curry: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _Haskell: https://www.haskell.org/
.. _Curry Homepage: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _Functional Programming: https://www.wikipedia.org/wiki/Functional_programming
.. _Logic Programming: https://www.wikipedia.org/wiki/Logic_programming

