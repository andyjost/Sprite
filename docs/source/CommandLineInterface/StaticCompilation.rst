.. highlight:: bash

==================
Static Compilation
==================

``sprite-make`` is used to convert Curry source files.  One may select which
stages of the :ref:`Compilation Pipeline <Introduction/CompilationPipeline:The
Curry Compilation Pipeline>` to run.

Sprite uses this program to compile the Curry library before installation.  Users
can rely on it to statically compile Curry programs.

Using ``sprite-make``
=====================

To view the help content say::

    sprite-make -h

For more detailed information say::

    sprite-make --man

Generating ICurry
-----------------

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
---------------

To generate JSON, supply ``--json``::

    sprite-make --json Peano.curry -o Peano.json

Since ICurry is a prerequisite of JSON in the compilation pipeline, building
JSON implies building ICurry.

Additional options are provided to compact JSON with ``jq`` (``--compact``),
compress it with ``zlib`` (``--zip``), and remove intermediate files
(``--tidy``).


Generating Backend-Specific Code
--------------------------------

Additional targets generate backend-specific code.  For the Python backend, the
following option is available:

``--py``
    Compiles the program to Python.  The output file can be run standalone or
    imported into Python.

..
    For the LLVM backend, the following options are available:

    ``--llvm``
        Generates LLVM IR.

    ``--as``
        Generates platform-specific assembly.

    ``--elf``
        Generates a platform-specific ELF object.


Specifying Curry files
----------------------

Similar to ``sprite-exec``, Curry files can be specified by their file name or
module name.  To treat names as Curry modules, suply ``-m`` and set CURRYPATH,
if needed, as described :ref:`here
<CommandLineInterface/RunningCurryPrograms:Finding Curry Code>`.

Creating Executables
====================

To create an executable file, supply ``sprite-make`` with ``--exe``.  The type
of executable file created depends on the backend selected.  This can be
controlled with ``--backend``.  For example::

    sprite-make --backend=py --exe Peano.curry -o Peano.py

(Show how to call the compiled program.)
