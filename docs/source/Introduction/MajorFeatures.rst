Major Features of Sprite
========================

Compile and Run Curry Programs
------------------------------

Sprite provides several ways to transform and run Curry code.  It implements a
static compiler that converts Curry files into executable formats.  It provides
a command-line program to execute Curry files in script-like fashion.  It
provides a Python API with which one can define or load Curry code dynamically,
JIT-compile, and execute it.


Python API
----------

All the features of Sprite are available through the Python API.  Say ``import
curry`` from Python to access it.  Using the Python API, it is possible to
compile and run Curry programs, inspect intermediates, build goals, dynamically
generate Curry modules, and much more.

Important characteristics of this API include the following:

- The barriers to entry for developers unfamiliar with Curry, Functional-Logic
  Programming, or Haskell are greatly lowered.  Since Sprite is presented as a
  Python extension, anyone familiar with Python can try Curry with only a
  slight effort.

- Curry can be used transparently from Python.  Sprite installs import hooks to
  search CURRYPATH for Curry modules.  A simple ``import`` statement
  suffices to locate, load, and compile Curry code, then expose it as a regular
  Python module.

- Built-in types are automatically converted between Curry and Python.
  Conversions are provided for numbers, Booleans, characters, strings, lists,
  and tuples.  Types defined in Curry are reflected in Python.

- Semantics are preserved when crossing the Curry-Python boundary.  Curry
  computations are represented in Python as generators, which are lazy objects
  whose only method is a function ``next`` that produces the next result.  This
  preserves the essential semantics of Curry, namely lazy evaluation and
  multi-valued expressions.  The reciprocal relation also holds: delayed Python
  computations are represented in Curry as infinite lists.

- Curry code can be embedded in Python or generated dynamically.  Sprite
  provides a function to compile strings containing Curry code into evaluable
  runtime objects.  Curry code can in this way be embedded into Python files
  (as strings) or generated on the fly.


The Backend
-----------

A backend of Sprite comprises a compiler and a runtime library.  The
compiler translates Sprite Intermediate Representation (IR) to the IR of
the backend.  The runtime library runs Curry programs.  The backends live
under ``src/python/backends``, behind the interface
:class:`IBackend <curry.backends.IBackend>`.

**C++ Backend**
    The C++ backend compiles each Curry module to C++ and links it against
    a runtime written in C++ with efficiency as the goal.  A module whose
    object is not ready runs interpreted from its ICurry by the interpreter
    of the same runtime, and the compile runs in the background (the
    interpreter flag ``interpret``; see :mod:`curry.interpreter.flags`).
    So a program starts at once, and an installation without a C++
    compiler runs every program interpreted; see
    :doc:`/Installation/WithoutCompiler`.


Command-Line Tools
------------------

Executable programs provided by Sprite are located under the ``bin`` directory
of the installation tree.  After saying ``make stage``, these programs can be
found under ``./install/bin/`` relative to the repository root.

Sprite provides the following command-line tools:

``python``
    A wrapper around the Python executable that Sprite was configured to use.
    Python will be started by ``sprite-invoke`` to ensure the environment is
    set up correctly for Sprite.

``sprite-exec``
    Executes a Curry script.  The argument is a Curry source file or module
    name.  Needed Curry modules are located via the CURRYPATH environment
    variable.  This program compiles the Curry, evaluates its ``main`` goal (or
    another goal specified by the ``-g`` option) and prints all values
    obtained.

``sprite-invoke``
    A wrapper script that configures the runtime environment for Sprite and
    then executes another program.  Environment variables such as PYTHONPATH,
    CURRYPATH, and LD_LIBRARY_PATH may be modified.

``sprite-make``
    Invokes the Sprite compilation pipeline.  This can be used to convert Curry
    code into a variety of formats.

