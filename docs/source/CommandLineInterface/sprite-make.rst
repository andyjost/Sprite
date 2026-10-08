.. highlight:: bash

.. _sprite-make:

===============
``sprite-make``
===============

``sprite-make`` is used to convert Curry files into various other formats.  One
may select which stages of the :ref:`Compilation Pipeline
<Introduction/CompilationPipeline:The Curry Compilation Pipeline>` to run.
The targets are ICurry (``--icy``), JSON (``--json``), Python (``--py``),
C++ (``--cxx``) and the shared object of the C++ backend (``--so``); the
options ``--jobs``, ``--curry2icurry`` and ``--rewrite-flat`` are
described in the manual below.

Sprite uses this program to compile the Curry library before installation.
Users can rely on it to transform files for inspection, or to statically
compile Curry programs.

To view the help content say::

    sprite-make -h

For more detailed information say::

    sprite-make --man


``sprite-make`` Manual
======================

.. include:: sprite-make-usage.rst

.. include:: sprite-make-man.rst

Generating ICurry
=================

To convert a Curry file to ICurry, supply ``--icy``.  To convert
``Peano.curry``, for instance, say::

    cd examples
    sprite-make --icy Peano.curry

This places the output file in the subdirectory used for caching intermediates.
To print this location say::

    sprite-make --subdir

You can specify the output file with ``-o``::

    sprite-make --icy Peano.curry -o Peano.icy

Generating JSON
===============

To generate JSON, supply ``--json``::

    sprite-make --json Peano.curry -o Peano.json

Since ICurry is a prerequisite of JSON in the compilation pipeline, building
JSON implies building ICurry.

Additional options are provided to compact JSON (``--compact``),
compress it with ``zlib`` (``--zip``), and remove intermediate files
(``--tidy``).


Generating Python
=================

To compile Curry into an executable Python file, supply :ref:`sprite-make` with
``--py``::

    sprite-make --py Peano.curry -o Peano.py

The output file can be loaded with :func:`curry.load`:

    >>> Peano = curry.load('Peano.py')
    >>> 'Peano' in curry.modules
    True

The Python file can also be imported into Python in the normal way:

    >>> sys.path.insert(0, '.')
    >>> import Peano

The side-effects of the above two methods are identical to ``from curry.lib
import Peano`` except for how the code is located.

The output file can also be run as a program under the Python of the
installation; the file has no interpreter line of its own.  For this to do
anything interesting, compile with ``-g`` to name the goal::

    % sprite-make --py Peano.curry -o Peano.py -g main
    % install/bin/python Peano.py
    S (S O)

The saved program reads ``-g NAME`` and ``--help`` as ``sprite-exec`` does.
The Python form belongs to the Python backend: :func:`curry.load` reads it
there, and the C++ backend loads a shared object instead (below).


Generating Shared Objects
=========================

The C++ backend compiles each module into a shared object.  To build one
ahead of time, supply ``--so``.  This implies ``--cxx``, which writes the C++
source, and needs the C++ compiler that Sprite was configured with::

    sprite-make --so Peano.curry

The object is written to ``.curry/sprite-pakcs-<ver>/Peano.so``, beside its
ABI stamp (``Peano.so.abi``): a digest of the runtime headers, the flags
it was compiled with, the compiler of the build and the format of the
generated code, and the real path of the installation.  The compile
also stores the object, the C++ source and the stamp in the product cache,
from which a later compile of the same module under the same conditions
places them instead of running the compiler (``SPRITE_PRODUCT_CACHE``; see
:ref:`CommandLineInterface/EnvironmentVariables:Development Variables`).
The installation uses ``--py`` and ``--so`` to compile the Curry library for
both backends, so that the first import after ``make stage`` compiles
nothing.
