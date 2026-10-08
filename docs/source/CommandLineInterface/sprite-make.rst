.. highlight:: bash

.. _sprite-make:

===============
``sprite-make``
===============

``sprite-make`` is used to convert Curry files into various other formats.  One
may select which stages of the :ref:`Compilation Pipeline
<Introduction/CompilationPipeline:The Curry Compilation Pipeline>` to run.
The targets are ICurry (``--icy``), JSON (``--json``), C++ (``--cxx``) and
the shared object of the C++ backend (``--so``); the options ``--jobs``,
``--curry2icurry`` and ``--rewrite-flat`` are described in the manual
below.

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


Generating Shared Objects
=========================

The C++ backend compiles each module into a shared object.  To build one
ahead of time, supply ``--so``.  This implies ``--cxx``, which writes the C++
source, and needs the C++ compiler that Sprite was configured with::

    sprite-make --so Peano.curry

The object is written to ``.curry/sprite-pakcs-<ver>/Peano.so``, beside its
ABI stamp (``Peano.so.abi``): a digest of the runtime headers, the flags
it was compiled with, the compiler of the build and the format of the
generated code, and the real path of the installation.  The object has
the ``SONAME`` ``sprite-Peano.so.<format>`` and names the objects of the
modules it imports by their ``SONAME``, so it holds no path (``readelf -d``
shows none).  The compile
also stores the object, the C++ source and the stamp in the product cache,
from which a later compile of the same module under the same conditions
places them instead of running the compiler (``SPRITE_PRODUCT_CACHE``; see
:ref:`CommandLineInterface/EnvironmentVariables:Development Variables`).
The installation uses ``--so`` to compile the Curry library, so that the
first import after ``make stage`` compiles nothing.
