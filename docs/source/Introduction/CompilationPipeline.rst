
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
<https://arxiv.org/abs/1908.11101>`__.  This takes two steps.  The Curry
front end, a program that comes with PAKCS, translates the module and its
imports into `FlatCurry`_, the desugared and otherwise simplified program.
Then Sprite's own translation, :mod:`curry.toolchain.flat2icurry`, turns the
FlatCurry into ICurry.  That translation is a Python port of the external
program `icurry <https://cpm.curry-lang.org/pkgs/icurry.html>`__ 3.1.0,
available through the `Curry Package Manager`_, and it writes the same
``.icy`` text.  ``icurry`` itself remains an alternative route; see
``configure --with-icurry`` and the environment variable
``SPRITE_CURRY2ICURRY``.

Sprite calls the front end as ``icurry`` under PAKCS does, with the options
``--extended -D__PAKCS__=<ver>`` (see ``CURRY_FRONTEND_FLAGS`` in
``Make.config``) and the directories of the Curry path on ``-i``.  This
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

The oracle of the port is the overlay archive ``overlay-pakcs-3.4.1.tgz`` at
the root of the repository.  It holds the FlatCurry and ICurry files of every
test program, written by the pinned front end and by ``icurry`` 3.1.0, and
the FlatCurry interfaces of the Curry library.  The oracle of a library
module is its committed ``.icy`` file under ``curry/lib``.  The modules under
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
compile and rewrites the name on a hit.  The test drivers turn the cache on.


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

The target IR depends on the backend selected.  The Python backend, for
instance, generates Python, whereas the LLVM backend generates LLVM IR.  This
stage performs a straight-line translation of Sprite IR to target IR.


Target IR to Executable Code
----------------------------

Depending on the backend, additional conversions may be performed to produce
executable code.  LLVM IR is at this stage converted into assembly and then
machine-executable binary code.  The Python backend, on the other hand,
requires nothing because Python can be run directly under an interpreter.
Sprite writes the bytecode cache of a generated Python file beside it, under
``__pycache__``, when it writes the file, and loads the file through
``importlib``.  A file without a current cache, such as one from an older
installation, gets its cache when it is first loaded, whether or not Python
runs with ``-B``.  So CPython compiles a generated module once per change, not
in every process.  Even so, a package such as `PyPy`_ could in principle be
used to post-process Python code into a more efficient form.

The C++ backend compiles each generated module with ``g++`` into a shared
object the first time the module is used, and again when the runtime headers
change.  Each object records a digest of the installed headers it was compiled
against in a file beside it (``<module>.so.abi``).  An object whose record
differs from the installed headers is compiled again; a new copy of the same
runtime keeps every object.  Every module includes the header ``cyrt/cyrt.hpp``,
and parsing that header is most of the compile time of a small module.  So the
backend precompiles the header once per set of compiler flags and keeps the
result beside the installed headers.  See ``SPRITE_CXX_PCH_ROOT`` under
:ref:`CommandLineInterface/EnvironmentVariables:Development Variables`.

``make stage`` and ``make install`` compile the Curry library for both
backends into the installation, with ``sprite-make --py`` and ``sprite-make
--so`` (see :ref:`sprite-make`).  So the first import after an installation
compiles nothing, and an installation serves on a machine without a C++
compiler for programs that need no other compiled module.  When the
installation itself has no C++ compiler, the C++ part of this step is
skipped, and the C++ backend compiles the library on first use.


.. _FlatCurry: https://cpm.curry-lang.org/pkgs/flatcurry.html
.. _PAKCS manual: https://www.curry-lang.org/pakcs/Manual.pdf
.. _JSON: https://www.json.org/
.. _zlib: https://zlib.net/
.. _ICurry package: https://cpm.curry-lang.org/pkgs/icurry.html
.. _Curry Package Manager: https://www.curry-lang.org/tools/cpm/
.. _PyPy: https://pypy.org/
