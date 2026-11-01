.. _compilation-pipeline:
.. _Introduction/CompilationPipeline:The Curry Compilation Pipeline:

The Curry Compilation Pipeline
==============================

Sprite compiles a module through a series of steps. Each writes an
intermediate file for inspection and reuse. Sprite performs some steps
itself and calls external programs for others. :doc:`CompilationOptions`
describes how a program runs interpreted, compiled just in time or
compiled ahead of time.

.. _Introduction/CompilationPipeline:Curry to ICurry:

Curry to ICurry
---------------

The Curry front end (the package ``curry-frontend`` or ``pakcs-frontend``
of a PAKCS installation) translates the module and its imports into
FlatCurry. Sprite rewrites that file, then translates it to ICurry, the
intermediate language of the compiler. The optional ``icurry`` program
provides another route for the last step (``WITH_ICURRY`` and
``SPRITE_CURRY2ICURRY``). Both read the rewritten FlatCurry. The port is
checked byte for byte against independent ``icurry`` output in
compatibility mode; section 8 of ``tests/README`` describes the oracle.
The runtime route looks through root type signatures and keeps the front
end's completed case order.

The front end places its files under ``.curry/pakcs-<ver>/`` beside the
source: FlatCurry in ``M.fcy`` and its interface in ``M.fint``. Sprite
uses ``.curry/sprite-pakcs-<ver>/`` for ``M.icy`` and copies the interfaces
there. Both directories may hold ``M.icurry``: it is a Curry interface,
not ICurry. The selected tool pair determines ``<ver>``
(:doc:`Installation/SoftwareCompatibility`). The front end reads the
Curry library of the installation, rather than a separate PAKCS library.

The rewrite has two passes. A Boolean equality a guard requires to be
True becomes the constraint ``constrEq``: ``f x | x == 3 = x`` binds
``x`` as in PAKCS. An ``if`` condition keeps Boolean equality and can
suspend. The set0 lift turns ``set0 e`` over captured variables into a
``setk`` call, so those values stay outside the set
(:ref:`CurryPrimer/Semantics:Set functions`). The ``.fcy`` on disk is the
rewritten program. A stale product is translated again at first import;
``sprite-make --rewrite-flat M`` reruns the step by hand. The implementation
is in ``toolchain/flat2icurry/`` and the staleness check is documented in
``toolchain/_curry2icurry.py``.

The front end reports overlapping-rule warnings once per module through
the log at WARNING. ``SPRITE_FRONTEND_WARNINGS=0`` or ``sprite-make -q``
silences them. It runs once per change of a module and not at all when
its products are current. A source-text cache can retain its output;
see ``SPRITE_CACHE_FILE`` in :doc:`DevelopmentVariables`.

.. _Introduction/CompilationPipeline:JSON to Sprite IR:
.. _JSON to Sprite IR:

ICurry to a module image
------------------------

The ICurry reader parses ``M.icy`` into the Python model in
:mod:`curry.icurry`. The translator merges built-ins, validates the model,
runs the optimizer passes using import summaries from images and writes
``M.img``. The runtime attaches its declarations and bytecode directly.
The ICurry text remains the translation record and the oracle comparison
format. The typed boundary retains ``.fint`` and ``.icurry``.

The products in pipeline order are:

============== ==============================================
Product        Purpose
============== ==============================================
``M.curry``    Source
``M.icy``      ICurry translation record
``M.img``      Runtime bytecode and import summaries
``M.cpp``      Optional generated C++
``M.so``       Optional compiled object, with ``M.so.abi``
============== ==============================================

A read-only product directory and a module compiled from text use private
images in the process's temporary storage. The C++ emitter reads the
ICurry text and import-image summaries. Inspection and saving recover
function bodies from the ICurry text.

ICurry to machine code
----------------------

With ``interpret:off`` or ``sprite-make --so``, the compiler translates
ICurry to C++ and the C++ compiler writes a shared object. Each object
carries a stamp of the headers, flags and imports it was compiled with;
changed inputs make it stale (:ref:`sprite-make`).

Under the defaults, a module without a current object starts interpreted.
The JIT compiles hot functions through LLVM or the C++ backend and adopts
compiled steps at a scheduler safepoint. ``make stage`` compiles the
Curry library ahead of time. :doc:`DeveloperNotes` describes module images
and persistent LLVM objects.
