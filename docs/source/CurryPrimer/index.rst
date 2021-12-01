.. highlight:: haskell

============
Curry Primer
============

The Curry programming language is based on `Haskell`_.  These languages are
superficially very similar, with Curry representing only a small syntactic
extension to Haskell.  Despite this, Curry delivers a big semantic punch, as it
brings the entirety of logic programming to bear.

The most complete source of information about Curry is the `Curry Homepage`_.
In this document, a very brief introduction is provided to help orient
unfamiliar readers.

Curry is a Functional-Logic programming language.  This means it synthesizes
aspects of the `Functional Programming`_ and `Logic Programming`_ paradigms.
From functional programming it gets first-class, high-order, pure functions;
strict (a.k.a., lazy) evaluation; immutable data; and a declarative style of
case- and function distinction via pattern-matching.  From logic programming it
gets, generally, non-determinism, but more specifically logic variables,
search, and disjuntive control flow.

The most surprising -- and appealing -- of these are the logical features.
These possess a preternatural aspect that hints at something much more than the
more typical imperative paradigm.  Still, programming is an often mundane task
that benefits nothing at all from a a counter-intuitive way to skin the same
cat.  One may not wish to parse arguments preternaturally.  Therefore, a
helpful, though simplistic, way of understanding Curry is as a way to utilize
Logic Programming in an environment that is not entirely logic-based.  The
unique features of Logic Programming, though available, are couched in the more
practical Functional Programming domain.

Sprite extends this even further.  Practical as Functional Programming may be
relative to Logic Programming, the Imperative Programming paradigm is probably
still more practical, and without question more popular and more familiar to
the vast majority of software developers.  So, the effort of Sprite to embed
Curry within an imperative language can be seen as a way to combine all three
dominant programming paradigms -- Functional, Logic, and Imperative -- in a
single programming environment.  This way, the programmer can choose whichever
approach is best suited to a particular task.

.. toctree::
   :maxdepth: 1

   The Curry Type System  <TypeSystem>
   Curry Syntax           <Syntax>
   Curry Semantics        <Semantics>
