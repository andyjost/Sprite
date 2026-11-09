==================================
Compatibility with PAKCS and KiCS2
==================================

This page is for readers who want to run a Curry program or CPM package
from PAKCS or KiCS2 on Sprite. It explains what runs unchanged, what runs
with a different result, and what Sprite refuses.

Curry programs share code through CPM, the Curry Package Manager; its
index lists the published packages. A package may declare external
operations: operations that the Curry system implements in its host
language instead of in Curry. Several packages declare externals that
only PAKCS implements. Sprite implements most of them; it refuses some
by design and lacks some that need outside tools.

The `dissertation's semantics <https://doi.org/10.15760/etd.3564>`_ is the
reference. Sprite supports a language construct or external operation
when its set of results does not depend on the schedule or search order.
Where PAKCS gives an operation its meaning through left-first search,
Sprite raises a named error. PAKCS is evidence, not the definition.
The developer notes state the :ref:`CPM support rule
<DeveloperNotes:CPM support rule>` (#262).

.. include:: CompatibilityTables.inc
   :start-after: begin-counts
   :end-before: end-counts

What runs unchanged
===================

Curry's language and standard library provide the shared basis for
programs that run unchanged on Sprite.
Sprite ships the base 3.4.0 library with its own set functions.
The sections below describe set functions and the discipline for global
state; later sections describe the limits that can affect a port.

The pinned checks pass for |cpm-pass-count| CPM packages.
A pass records the check for that package version, not every possible
program that uses it. The :ref:`package table
<Compatibility:CPM packages>` lists the results.

Weak encapsulation by set functions
-----------------------------------

Set functions preserve the distinction between choices in a function
body and choices in its arguments.
A set function captures choices in the body. Choices in its arguments
stay outside. This is weak encapsulation, as described in the
:ref:`Curry primer <CurryPrimer/Semantics:Set functions>`:

.. code-block:: haskell

    module Weak where
    import Control.SetFunctions
    f :: Int -> Int
    f x = x ? (x + 1)
    main :: [Int]
    main = sortValues (set1 f (1 ? 5))

Sprite and PAKCS 3.10.0 both print:

.. code-block:: text

    [1,2]
    [5,6]

Each outside choice gets its own set. The primer also explains outside
failures and captured variables. KiCS2's `manual, section 1.3, page 7
<https://www.curry-lang.org/kics2/Manual.pdf#page=8>`_ describes set
functions as weak encapsulation too.

Global state with Data.Global
-----------------------------

Sprite supports ``Data.Global`` from the ``global`` package under the
discipline of that package.
Declare a global at the top level and give it a ground initial value.
For a temporary global, use its qualified name as the key and a concrete
type. The `package documentation
<https://cpm.curry-lang.org/DOC/global-3.2.0/Data.Global.html>`_ describes
this interface:

.. code-block:: haskell

    module Example where
    import Data.Global
    counter :: GlobalT Int
    counter = globalT "Example.counter" 0

Sprite requires a closed initializer for ``globalT``. If the initializer
reaches a caller's choice, binding or free variable, Sprite raises
``EvaluationError`` with the key's name. A second definition of a key must
give the same initial value or raise the same error. One ground value becomes the
initial value; no value fails; multiple values raise an error with the
key's name. The :ref:`developer notes <DeveloperNotes:Primitives>` and
:doc:`ReleaseNotes` record this rule (#266).

What runs with a different result
=================================

These programs are valid input to both systems, but Sprite and PAKCS
3.10.0 produce different output when they run.

Fair search and depth-first search
----------------------------------

Fair search can find an answer while another alternative diverges.
PAKCS's depth-first search can stay in that alternative:

.. code-block:: haskell

    module Fair where
    loop :: Int
    loop = loop + 1
    main :: Int
    main = loop ? 7

The first answer in Sprite, via
``curry.show(next(curry.eval(module.main)))``, is:

.. code-block:: text

    7

PAKCS printed no answer before the test stopped it after five seconds.
This is a bounded observation. The recursive left alternative has no
base case.

KiCS2 offers several search strategies. Its `manual, section 2.3, page 12
<https://www.curry-lang.org/kics2/Manual.pdf#page=13>`_ states that
breadth-first search is the default. The depth-first
observation above applies to PAKCS.

A choice at an I/O step
-----------------------

A choice that reaches an I/O step can affect the output before an error.
Sprite raises ``NondetError`` at that step. The pinned ``flatcurry-xml``
exception records this rule as class 2
(`#216 <https://github.com/andyjost/Sprite/issues/216>`_):

.. code-block:: haskell

    module ChoiceIO where
    guarded :: Bool -> IO ()
    guarded b = if b then putStrLn "yes" else return ()
    main :: IO ()
    main = guarded (True ? False)

Sprite prints no ``yes`` and reports:

.. code-block:: text

    ERROR: non-determinism in monadic actions occurred!

PAKCS prints ``yes`` before it reports its error:

.. code-block:: text

    yes
    ERROR: non-determinism in I/O actions occurred!

What Sprite refuses
===================

Sprite refuses the external operations in these three categories with
an error that names the operation and the reason.

Strong encapsulation
--------------------

Strong encapsulation captures nondeterminism from outside the call too.
Sprite refuses the strong-encapsulation externals in the table below
because their results depend on evaluation order (class 1).
For example, with ``allvalues`` 4.0.0:

.. code-block:: haskell

    module Strong where
    import Control.AllValues (allValues)
    main :: [Int]
    main = allValues (1 ? 2)

Sprite reports:

.. code-block:: text

    ERROR: Control.AllValues.allValues: not supported by Sprite: strong encapsulation; its results depend on the evaluation order (see https://andyjost.github.io/Sprite/Compatibility.html)

PAKCS 3.10.0 prints:

.. code-block:: text

    [1,2]

The `package source
<https://cpm.curry-lang.org/DOC/allvalues-4.0.0/Control.AllValues_curry.html>`_
documents the dependence on rule order. Use set functions when weak
encapsulation suits the program. KiCS2's `manual, section 1.3, page 7
<https://www.curry-lang.org/kics2/Manual.pdf#page=8>`_ describes strong
encapsulation through I/O operations and programmable search trees.

Backtrackable global variables
------------------------------

``GlobalVariable`` from ``global-variables`` provides global values whose
updates follow backtracking.
Sprite refuses its externals because their values depend on search
order (class 1). For example, a call to ``prim_writeGVar`` meets:

.. code-block:: text

    ERROR: GlobalVariable.prim_writeGVar: not supported by Sprite: backtrackable global variables; their values depend on the search order (see https://andyjost.github.io/Sprite/Compatibility.html)

Use ``Data.Global`` for global state under the discipline above.

PAKCS constraint solvers
------------------------

The ``clp-pakcs`` and ``clpbool`` packages expose PAKCS constraint solvers.
Sprite refuses their externals because they bind to the Prolog back end
of PAKCS (class 4). For example, a call to ``CLP.R.prim_CLPR_i2f`` meets:

.. code-block:: text

    ERROR: CLP.R.prim_CLPR_i2f: not supported by Sprite: PAKCS constraint solvers; they are bound to the Prolog back end of PAKCS (see https://andyjost.github.io/Sprite/Compatibility.html)

Refused modules and operations
------------------------------

This table lists the refused modules and the scope of each refusal.

.. include:: CompatibilityTables.inc
   :start-after: begin-refusals
   :end-before: end-refusals

CPM packages
============

This table records the pinned checks for |cpm-tested-count| packages from
the CPM index dated |cpm-index-date|, which lists |cpm-index-count| packages.
The records contain |cpm-pass-count| passes, |cpm-exception-count| known
exceptions and |cpm-open-count| open entry.
The source is :download:`index-expected.json
<../../tests/data/cpm/index-expected.json>`; its index SHA256 is
|cpm-index-sha256|.

Each known exception has one of five classes:

1. Results depend on the schedule or search order, as in strong
   encapsulation and backtrackable global variables under "What Sprite
   refuses".
2. Sprite applies a stricter rule than PAKCS, as in the choice at an I/O
   step under "What runs with a different result".
3. The package installs a module that the runtime implements, so Sprite
   refuses that source copy (``base`` and ``setfunctions``).
4. The package binds a PAKCS constraint solver, whose externals require
   PAKCS's Prolog back end (``clp-pakcs`` and ``clpbool``).
5. An external tool is absent, or the package is broken upstream under
   PAKCS too.

The open entry is ``currypp``: Contracts times out (#247, caused by #251),
and DefaultRules times out (#242). :doc:`Status` lists known defects,
such as the functional-pattern sharing defect
`#251 <https://github.com/andyjost/Sprite/issues/251>`_.

.. include:: CompatibilityTables.inc
   :start-after: begin-packages
   :end-before: end-packages
