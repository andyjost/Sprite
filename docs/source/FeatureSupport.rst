===============
Feature Support
===============

Sprite supports a CPM feature when its set of results does not depend on
the schedule or search order. If a feature gets its meaning from PAKCS's
left-first search, Sprite raises a named error. The
:ref:`CPM support rule <DeveloperNotes:CPM support rule>` gives the policy
and its reasons (#262).

Every known exception in the pinned index has one of five classes:

1. Results depend on the schedule or search order.
2. Sprite is stricter than PAKCS under a rule that does not depend on the
   schedule.
3. The package installs a module that the runtime implements.
4. The package binds a PAKCS constraint solver.
5. An external tool is absent, or the package is broken upstream under
   PAKCS too.

The `dissertation's semantics <https://doi.org/10.15760/etd.3564>`_ is the
reference. PAKCS provides evidence for comparisons. The examples below
were checked with Sprite and PAKCS 3.10.0. :doc:`Status` lists current
defects, including the functional-pattern sharing defect
`#251 <https://github.com/andyjost/Sprite/issues/251>`_.

Fair search and depth-first search
==================================

Sprite's fair search can find an answer while another alternative
diverges. PAKCS's depth-first search can stay in that alternative:

.. code-block:: haskell

    module Fair where
    loop :: Int
    loop = loop + 1
    main :: Int
    main = loop ? 7

Requesting the first answer in Sprite, with
``curry.show(next(curry.eval(module.main)))``, prints:

.. code-block:: text

    7

Evaluating ``main`` in PAKCS printed no answer before the test stopped it
after five seconds. This is a bounded observation. The recursive left
alternative has no terminating case.

KiCS2 offers several search strategies. Its default is breadth-first
search, according to its `manual, section 2.3, page 12
<https://www.curry-lang.org/kics2/Manual.pdf#page=13>`_. The depth-first
observation above applies to PAKCS.

Weak encapsulation by set functions
===================================

A set function captures choices in the function body. Choices in its
arguments stay outside. This is weak encapsulation, as described in the
:ref:`Curry primer <CurryPrimer/Semantics:Set functions>`:

.. code-block:: haskell

    module Weak where
    import Control.SetFunctions
    f :: Int -> Int
    f x = x ? (x + 1)
    main :: [Int]
    main = sortValues (set1 f (1 ? 5))

Sprite and PAKCS both print:

.. code-block:: text

    [1,2]
    [5,6]

Thus each outside choice gets its own set. Weak encapsulation is shared
behavior in this example. The primer explains outside failures and
captured variables too. KiCS2's `manual, section 1.3, page 7
<https://www.curry-lang.org/kics2/Manual.pdf#page=8>`_ also describes set
functions as weak encapsulation.

Strong encapsulation
====================

Strong encapsulation captures nondeterminism from outside the call too.
Sprite refuses the missing externals listed below for this feature.
Their results depend on evaluation order (class 1). For example, using
``allvalues`` 4.0.0:

.. code-block:: haskell

    module Strong where
    import Control.AllValues (allValues)
    main :: [Int]
    main = allValues (1 ? 2)

Sprite reports:

.. code-block:: text

    ERROR: Control.AllValues.allValues: not supported by Sprite: strong encapsulation; its results depend on the evaluation order (see the page Feature Support of the documentation)

PAKCS prints:

.. code-block:: text

    [1,2]

The `package source
<https://cpm.curry-lang.org/DOC/allvalues-4.0.0/Control.AllValues_curry.html>`_
documents the dependence on rule order. KiCS2's `manual, section 1.3,
page 7 <https://www.curry-lang.org/kics2/Manual.pdf#page=8>`_ describes
strong encapsulation through I/O operations and programmable search trees.

A choice at an I/O step
=======================

Sprite raises ``NondetError`` when a choice reaches an I/O step.
The pinned ``flatcurry-xml`` exception records this rule as class 2
(`#216 <https://github.com/andyjost/Sprite/issues/216>`_).
This example shows why a PAKCS program can produce different output:

.. code-block:: haskell

    module ChoiceIO where
    guarded :: Bool -> IO ()
    guarded b = if b then putStrLn "yes" else return ()
    main :: IO ()
    main = guarded (True ? False)

Sprite prints no ``yes`` and reports:

.. code-block:: text

    ERROR: non-determinism in monadic actions occurred!

PAKCS prints ``yes`` before reporting its error:

.. code-block:: text

    yes
    ERROR: non-determinism in I/O actions occurred!

Global state
============

Sprite supports ``Data.Global`` from the ``global`` package with the
discipline of that package: declare a global at the top level and give
it a ground initial value. For a temporary global, use the qualified
name as its key and a concrete type. The `package documentation
<https://cpm.curry-lang.org/DOC/global-3.2.0/Data.Global.html>`_ describes
this interface. For example:

.. code-block:: haskell

    module Example where
    import Data.Global
    counter :: GlobalT Int
    counter = globalT "Example.counter" 0

The pinned ``global`` check passes. ``GlobalVariable`` belongs to the
separate ``global-variables`` package. Sprite refuses its missing
externals because backtrackable global values depend on search order
(class 1).

.. include:: FeatureSupportTables.inc
