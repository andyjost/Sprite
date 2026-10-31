
.. _compilation-pipeline:

The Curry Compilation Pipeline
==============================

Sprite compiles Curry programs via a series of transformations.  Each
transformation, called a `stage`, is associated with certain type of
intermediate file.  Intermediate files are used to checkpoint, debug, and
inspect the build process.  A transformation might be implemented by Sprite or
performed by an external program.  Taken in order, the stages form the
compilation pipeline.  Sprite chooses as its starting point the newest
among a Curry source file and all its intermediates along the pipeline.

The following sections discuss the compilation stages in detail.


Curry to ICurry
---------------

Sprite first translates Curry source code into a format called `ICurry
<https://arxiv.org/abs/1908.11101>`__.  This takes three steps.  The Curry
front end, a program that comes with PAKCS, translates the module and its
imports into `FlatCurry`_, the desugared and otherwise simplified program.
The rewrite step then rewrites the FlatCurry file in place, with the
binding optimization of PAKCS and the set0 lift (see below).  Then
Sprite's own translation,
:mod:`curry.toolchain.flat2icurry`, turns the FlatCurry into ICurry.  That
translation is a Python port of the external program `icurry
<https://cpm.curry-lang.org/pkgs/icurry.html>`__ 3.3.0 (3.1.0 for the legacy pair), available through
the `Curry Package Manager`_, and it writes the same ``.icy`` text.
``icurry`` itself remains an alternative route for the last step; see
``CMake WITH_ICURRY`` and the environment variable
``SPRITE_CURRY2ICURRY``.  It reads the rewritten file too, so both routes
write the same ``.icy`` file.

Sprite calls the front end as ``icurry`` under PAKCS does, with the options
``--extended -D__PAKCS__=<ver>`` (see ``frontend_flags`` in the
``sysconfig`` directory of the installation) and the directories of the Curry path on ``-i``.  This
affects where certain intermediate files are placed.  For details refer to the
`PAKCS manual`_.  In short, the front end places its files under
``.curry/pakcs-<ver>/``, relative to the original Curry source files, where
``<ver>`` is replaced with the numeric PAKCS version.  Among other files, it
places the FlatCurry intermediate here, with extension ``.fcy``, and the
FlatCurry interface of each module it compiles, with extension ``.fint``.
The translation reads the interfaces of the imports from there.

Sprite uses a similar scheme to store intermediate files.  The intermediate
directory used by Sprite is named ``.curry/sprite-pakcs-<ver>``.  The
ICurry file is placed here with extension ``.icy``.

The Curry library that the front end reads is Sprite's own copy under
``curry/`` in the installation tree.  Sprite puts that directory on the
search path; the library of PAKCS is not consulted.

The command ``python -m curry.toolchain.flat2icurry M.fcy`` runs the
translation by hand, and ``tests/lib/flat2icurry_oracle.py`` compares its
output with the ``.icy`` files that ``icurry`` wrote.

The oracle of the port is the overlay archive ``overlay-pakcs-3.10.0.tgz``
under ``tests/overlay/``.  It holds the FlatCurry and ICurry files of every
test program, written by the pinned front end and by ``icurry`` 3.3.0, and
the FlatCurry interfaces of the Curry library.  The current archive also holds all library oracles. The legacy pair
uses ``overlay-pakcs-3.4.1.tgz`` with ``icurry`` 3.1.0 references.  The modules under
``tests/data/curry/flat2icurry`` probe what the rest of the corpus does not
use, such as negative numbers, newtypes, and recursive lets.  The unit test
``unit_flat2icurry.py`` checks a fixed sample of 60 files and the probes;
``func_flat2icurry.py`` checks the whole archive.  The command
``python tests/lib/flat2icurry_oracle.py --overlay`` does the same by hand.
``make overlay-archive`` rebuilds the archive from the products on disk.
Run it only after the products were written by ``icurry``
(``SPRITE_CURRY2ICURRY=icurry``); the port must not become its own oracle.

One defect of ``icurry`` 3.1.0 is kept behind a flag.  A type annotation at
the root of a rule, as in ``f x = (let y = x in y) :: Int``, hides the
expression under it from the block builder.  The bindings of a let or a free
declaration are lost, and a case is an error.  A program with such a rule
fails at run time.  The flag ``icurry_compat`` of
:func:`curry.toolchain.flat2icurry.translate` copies the defect.  It is on
by default, and the oracle tests keep it on, so the output stays
byte-identical to the oracle.  The build route (``sprite-make`` and the
import of a module) turns it off and looks through the annotation.  The
option ``--no-icurry-compat`` of the command line does the same.

Between the front end and the translation, both routes apply the rewrite
step to the FlatCurry file (:func:`curry.toolchain.flat2icurry.rewrite_file`),
two passes in order: the binding optimization
(:mod:`curry.toolchain.flat2icurry.bindingopt`) and the set0 lift
(:mod:`curry.toolchain.flat2icurry.setlift`).  PAKCS and KiCS2 run the
tool ``transbooleq`` over every FlatCurry file they compile (the property
``bindingoptimization`` of PAKCS, ``fast`` by default), and the pass is a
port of its fast mode.  A Boolean equality whose value is required to be
True becomes the equational constraint ``constrEq``, which binds free
variables where ``==`` on a primitive type suspends: ``f x | x == 3 = x``
binds ``x``, and so does a conjunct of ``&&`` or ``&`` in a guard; an
``if-then-else``, a guard with an ``otherwise`` branch, and ``||`` keep the
Boolean equality.  A disequality under ``not`` becomes a negated
constraint.  The pass also changes a program as PAKCS changes it: ``&``
requires both arguments True whatever its result is required to be, so
``(1 == 2) & True`` fails instead of being False.  The pass is what lets a
program in the residuation style of ``sendMoreMoney`` (tests/data/curry)
solve: without it the digit equalities suspend, under PAKCS as well
(``pakcs -Dbindingoptimization=no``).

The set0 lift makes the captured variables of ``set0 e`` arguments of
the capsule (decision D28 of 2026-10-12).  A call ``set0 e`` whose
expression ``e`` holds variables of the enclosing context, ``x1 .. xk``,
becomes ``setk L x1 .. xk``, with a new private function
``L x1 .. xk = e`` (``set1 (L x1 .. x(k-1)) xk`` beyond seven, the
arities the library has).  The runtime boxes the arguments of ``setk``
at the entry of the capsule, so the non-determinism and the failure of a
captured variable stay outside the set, one set per outside alternative,
as the semantics of weakly encapsulated search prescribes (see
:ref:`CurryPrimer/Semantics:Set Functions`).  A class dictionary and a
free variable of an enclosing ``where`` are captured variables like any
other; a ``set0`` inside a lambda or a local definition is lifted out of
the function the front end made for it; ``set0 $ e`` is the call
``set0 e``.  A closed ``set0 e`` (no captured variable) is unchanged.
The pass does not reach a ``set0`` that is not a saturated call, such as
the partial application in ``map set0 xs``: it sees no argument there,
and the element reaches ``set0`` at run time as a closed expression.

As PAKCS does (``preprocessFcyFile`` of its compiler), Sprite applies the
step to the file itself.  When a pass changes the program, ``M.fcy`` is
written again, in the format of the front end (a file of the front end
read and written again is byte-identical); otherwise the file is left as it
is, with its time.  A second run over a rewritten file changes nothing.  So
the ``.fcy`` on disk is the rewritten program, the ``icurry`` program reads
it too, and the two routes write the same ``.icy`` file.  The oracle tests
do not apply the step: the files ``icurry`` wrote for the archive come from
the FlatCurry as the front end wrote it.  The option ``--rewrite`` of
the command line ``python -m curry.toolchain.flat2icurry`` applies the
step to the program in memory and leaves the file alone (the flag
``rewrite`` of :func:`curry.toolchain.flat2icurry.translate`).

The rewrite covers every FlatCurry file a run of the front end wrote.  A
run on ``M`` compiles more than ``M``: an import whose files are missing,
older than its source, or older than the interface of one of its own
imports is compiled again, and its ``.fcy`` is written again in the text
of the front end, while its ICurry stays current by the rule of the
toolchain.  So the step runs over the files of those imports too, and the
FlatCurry file beside an ICurry file never lacks the rewrite the ICurry
has.  One writer outside the toolchain leaves such a file: the PAKCS
oracle of the tests (section 8 of ``tests/README``).

The step reaches the modules the routes translate.  The committed ICurry of
the Curry library predates it and is not regenerated by the step; the
``.icy`` of a library module changes only when the module is translated
again (``SPRITE_REBUILD_ICY=1``), and then from its rewritten FlatCurry
(no library module uses ``set0``).  A product translated before the file
was rewritten by a pass is stale: the FlatCurry file beside the source
holds a Boolean equality the binding optimization replaces, and neither it
nor the ICurry file holds ``constrEq``; or it holds a ``set0`` call the
lift lifts, and the ICurry file lacks the lifted function
(``translated_before_rewrite`` of ``curry.toolchain._curry2icurry``; the
modules of the library are not judged, and the check costs a read of the
FlatCurry file on an import, a parse when the text has an equality name
and no ``constrEq`` or names ``set0``, once per process and for a file up
to 256 KB; a larger file, and a file that cannot be written again, are
not judged, with a warning).  The step from Curry to ICurry runs again at
the first import of the module, as for a changed source: the front end
leaves the current file, the step rewrites it, and the translation
follows;
``sprite-make`` prints how many modules it made again so, and how many
the ICurry cache of the test drivers served instead (a hit rewrites the
FlatCurry file as well; see the cache below).  To run the step
for a module by hand, current or not, run ``sprite-make --rewrite-flat M``:
it rewrites the FlatCurry file, and makes the ICurry and the later products
from it; the option implies ``--icy`` and stands alone.  The command
``python -m curry.toolchain.flat2icurry.rewrite M.fcy`` rewrites FlatCurry
files alone.

The front end warns on overlapping rules ("Function f is potentially
non-deterministic due to overlapping rules"), the shape under which
``build 0 = ...; build n = ...`` compiles to a choice whose second
alternative is infinite.  A run of the front end reports that warning
once per module through the log at the WARNING level, with the text of the
front end, so an import, ``curry.compile`` and ``sprite-make`` show it on
the standard error stream; the other warnings of the front end
(non-exhaustive patterns, missing signatures, unused bindings) stay quiet.
A module compiled from its products or from the ICurry cache runs no front
end and gives no warning.  ``SPRITE_FRONTEND_WARNINGS=0`` and
``sprite-make -q`` silence the warnings (see
:ref:`CommandLineInterface/EnvironmentVariables:User Variables`).

.. note::
   The PAKCS subdirectory may contain a file with extension ``.icurry``.  That
   file does `not` contain ICurry (it contains a Curry `interface`).

The front end takes seconds per module.  Sprite can keep its output in a
cache, an SQLite database named by ``SPRITE_CACHE_FILE`` (see
:ref:`CommandLineInterface/EnvironmentVariables:Development Variables`).  The
key of an entry is a digest of the module source, of the sources of the
modules it imports, of the front-end options, and of the route from Curry to
ICurry with its program and flags; the file name is not part of it.  So an
entry written by one route is never served to the other.  A module compiled
from a string by ``curry.compile`` gets a new name
in every process.  The cache stores its ICurry under the name of the first
compile and rewrites the name on a hit.  A hit writes the ICurry file and
runs the binding optimization over the FlatCurry file of the front end
beside the source as well, when the file is current (``rewrite_on_hit`` of
``curry.toolchain._curry2icurry``), so the pair on disk agrees as after a
translation; a file older than the source, of another version of it, is
left to the next run of the front end.  The test drivers turn the cache on.


ICurry to JSON
--------------

``.icy`` files are formatted using a subset of Curry.  To facilitate their use
in other programming environments, which may not have a Curry parser, Sprite
converts them to `JSON`_.  This conversion is handled by a pure-Python parser
that implements a sufficient subset of Curry.

To compensate for the space inefficiency of JSON, Sprite writes the JSON in a
compact form and compresses it with `zlib`_.  The compact form has no space
after a comma or a colon, and it escapes every character outside ASCII.
Compressed ICurry-JSON files use suffix ``.json.z``.


JSON to Sprite IR
-----------------

Sprite's in-memory IR closely reflects `ICurry`.  This is implemented in Python
under :mod:`curry.icurry`.  That module also provides functions to load ICurry
from JSON or native ICurry, and to dump ICurry into a human-readable format or
as JSON.

The in-memory representation is suitable for viewing and transforming ICurry.
Using the Python API, one can inspect ICurry interactively from Python or
manipulate it from Python scripts.


Sprite IR to Target IR
----------------------

The target IR of the C++ backend is C++.  This stage performs a
straight-line translation of Sprite IR to target IR.


Target IR to Executable Code
----------------------------

The C++ backend compiles the generated C++ into a shared object (below), or
interprets the ICurry of the module until the object is ready.

The C++ backend compiles each generated module with ``g++`` into a shared
object the first time the module is used, and again when the runtime headers
the generated code includes change.  Each object records a digest of those
headers (the include closure of ``curryrt/curryrt.hpp``; a header of the runtime
outside it rebuilds the runtime library alone), of the flags it was
compiled with, of the compiler the runtime was built with and of the format
of the generated code, and the real path of the installation it was
compiled under, in a file beside it (``<module>.so.abi``, the ABI stamp).
ICurry records its direct imports' interface digests in ``<module>.icy.imports``;
generated C++ and ABI stamps also record imported ICurry content for inlining,
and a missing record or a changed import makes the corresponding product stale.
An object whose digest differs from the installed headers of the closure,
or whose path is not this installation, is compiled again; a new copy of
the same runtime keeps
every object, and a package whose manager rewrote the path at install time
keeps its objects.  The object itself names no path: it carries the
``SONAME`` ``sprite-<module>.so.<format>`` and names the objects of its
imports by their ``SONAME``, which the dynamic linker satisfies with the
objects the loader has opened before it (the loader opens the imports of
an object first), and its record names the source relative to the
installation or to the object.  So an object compiled in one tree loads in
a copy of the tree at another path.  A compile also stores the object, the generated C++ and
the stamp in the product cache, and a later compile of the same module under
the same conditions places them from there instead of running the compiler;
see ``SPRITE_PRODUCT_CACHE`` under
:ref:`CommandLineInterface/EnvironmentVariables:Development Variables`.
Every module includes the header ``curryrt/curryrt.hpp``,
and parsing that header is most of the compile time of a small module.  So the
backend precompiles the header once per set of compiler flags and keeps the
result beside the installed headers.  See ``SPRITE_CXX_PCH_ROOT`` under
:ref:`CommandLineInterface/EnvironmentVariables:Development Variables`.

``make stage`` and ``make install`` compile the Curry library into the
installation with ``sprite-make --so`` (see :ref:`sprite-make`).  So the
first import after an installation
compiles nothing of the library. Under the default ``interpret:new``, a
module without a current object starts interpreted from its ICurry.
The default ``jit:hot,jit_backend:auto`` compiles hot functions with LLVM
when llvmlite imports, otherwise whole modules in a child process with gxx
when a C++ compiler is available. Compiled steps are adopted at a scheduler
safepoint. With neither backend the interpreter runs alone with one notice;
see :doc:`/Installation/WithoutCompiler`.


.. _FlatCurry: https://cpm.curry-lang.org/pkgs/flatcurry.html
.. _PAKCS manual: https://www.curry-lang.org/pakcs/Manual.pdf
.. _JSON: https://www.json.org/
.. _zlib: https://zlib.net/
.. _ICurry package: https://cpm.curry-lang.org/pkgs/icurry.html
.. _Curry Package Manager: https://www.curry-lang.org/tools/cpm/
