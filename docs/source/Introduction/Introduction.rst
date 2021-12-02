Introduction
============

`Curry`_ is a Functional-Logic programming language with syntax based on
`Haskell`_.  Despite superficial similarities, Curry delivers a big
semantic punch, as it unifies disparate aspects of two of the foremost
programming paradigms.  From `Functional Programming`_ it acquires first-class,
higher-order, pure functions; strict (a.k.a., lazy) evaluation order; partial
application; immutable data; and pattern matching.  From `Logic Programming`_
it gains non-determinism, logic variables, and disjunctive control flow.

.. note::
  Learn about Curry at the `Curry Homepage`_.  The :ref:`Appendix
  <CurryPrimer/index:Curry Primer>` also provides a brief introduction intended
  to help orient unfamiliar readers.

The most exotic of these are the Logic Programming features.  They possess a
preternatural aspect that to a programmer familiar with only Functional or
Imperative styles can seem magical.  If one only describes an object's
properties, the runtime can deduce what that object must be and conjure it
seemingly out of thin air.  The execution state involves superpositions that
somehow take on multiple values at once.  Control flow is not linear or even
localized to a definite time or place; it rather branches out in exploratory
fashion, as would a parallel search.

These aspects hint at a tantalizing power that is somehow greater than what
Functional or Imperative languages seem to offer.  The potential to unlock this
has inspired `grand efforts`_.

And yet.

Programming is often mundane.  It benefits not at all from an unfamiliar, or
even counter-intuitive way to skin the same cat.  One may not, for example,
wish to parse command-line arguments "preternaturally" or open a file by
logical inference, whatever that may mean in practice.  A `purely` Logic
Programming language is limited to the extent that it forces programmers to do
everything on its terms.

Some might therefore regard Logic Programming as less practical than more
popular approaches.  And, indeed, if we measure practicality as the number of
commercial products developed, the data support this notion.  Not only that,
but the utility of a programming language must also be regarded as a function
of the size and quality of its community, libraries, and other resources, no
matter what properties the language itself may possess.  The question then
arises of how one can make the most appealing aspects of Logic Programming more
paletable to more potential users.

Functional-Logic programming is a broad effort to synthesize aspects of
Functional and Logic Programming.  In light of the above, it can perhaps be
understood as an effort to couch Logic Programming in terms of more widely used
Functional programming languages.  Curry, in one sense, makes Logic Programming
viable in a way that cleverly leverages the well-developed Haskell community
resources.  One can learn much of Curry by reading a Haskell tutorial.  And one
can write a mostly functional program that judiciously uses logic features
only where they make sense.

Sprite carries this idea to its logical conclusion.  By embedding Curry in
Python, Sprite allows one to switch effortlessly between Functional,
Imperative, and Logic styles.  Each function, module, or other component of an
application can choose whichever is most appropriate for the task at hand.

In doing so Sprite meets programmers where they are.  Python is an enormously
popular language.  By packaging Functional-Logic programming as a Python
extension, it instantly becomes approachable to a vast community.
With Sprite, anyone can use Functional and Logic Programming where it makes
sense, while relying on Python where it is preferred.

The remainder of this introduction gives a high-level overview of Sprite.  It
is intended to orient new users so that they may understand Sprite well enough
to begin using it.

.. toctree::
   :maxdepth: 1

   Major Features of Sprite        <MajorFeatures>
   External Softare                <ExternalSoftware>
   Project Layout                  <ProjectLayout>
   The Curry Compilation Pipeline  <CompilationPipeline>


.. _Curry: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _Haskell: https://www.haskell.org/
.. _Curry Homepage: https://curry.pages.ps.informatik.uni-kiel.de/curry-lang.org/
.. _Functional Programming: https://www.wikipedia.org/wiki/Functional_programming
.. _Logic Programming: https://www.wikipedia.org/wiki/Logic_programming
.. _grand efforts: https://en.wikipedia.org/wiki/Fifth_generation_computer

