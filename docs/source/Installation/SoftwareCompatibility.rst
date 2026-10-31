======================
Software Compatibility
======================

Sprite was developed and tested with the following software:

- Ubuntu Linux 24.04 LTS
- Python 3.14
- PAKCS 3.10.0, with the Curry front end 3.1.0 that it ships
- SWI-Prolog 9.0.4, which runs PAKCS (the test oracle); Sprite itself runs
  no Prolog
- g++ 13.3
- GNU Make 4.3
- pybind11 v3.1.0

macOS, Apple Silicon and Intel, builds the runtime and runs the C++
backend as Linux does, the compiled modules and the background compile of
the C++ compiler backend of the JIT included (issues #162 and #163), with the front end built
from source by the CI job of the repository.  The workflows of the
repository build the wheels of both packages, ``curry`` and
``curry-frontend``, for macOS 15 or newer on both architectures.

Windows x64 builds the runtime and the bindings with clang-cl of Visual
Studio on windows-2025 and runs every module interpreted: no generated
code is compiled there, and the JIT (``llvmlite``) is the compiled mode.
The workflows build the wheels of both packages for Windows as well; the
wheels vendor the C and C++ runtimes of Visual Studio.

Known compatibility problems are discussed below.

PAKCS
    Sprite ships a copy of the Curry library of PAKCS 3.10.0 (base 3.4.0) under
    ``curry/lib`` and relies on the internal interface of that Prelude, which
    is unstable.  PAKCS itself provides the Curry front end, which translates
    Curry to FlatCurry, and the test oracle.  The default configuration is front end 3.1.0 with PAKCS
    3.10.0. Front end 2.0.0 with PAKCS 3.4.1 remains supported, with advisory
    ``legacy-tools`` Linux unit and functional shards. Front-end packages
    are 2.0.0.post6 and 3.1.0.post2, with separate parity references; the
    distribution ``curry`` depends on 3.1.0, the version of its pinned
    library products, which 2.0.0 cannot read.

ICurry
    Sprite translates FlatCurry to ICurry itself.  Its translation is a port
    of the ICurry Compiler 3.3.0 (3.1.0 for the legacy pair) and writes
    the same files in compatibility mode.  That program,
    installed with the Curry Package Manager, remains an optional
    alternative; see ``CMake WITH_ICURRY``.  CMake checks the compiler version against the selected front end.

Curry preprocessor
    ``currypp`` is optional and is shipped by neither Sprite nor the
    front-end package. Modules whose OPTIONS_CYMAKE pragma names
    ``--pgmF=currypp`` need it on PATH when compiling from source.
    Install the preprocessor for your PAKCS installation with its Curry
    Package Manager, then put the package manager's executable directory
    on PATH:

    .. code:: bash

        cypm update
        cypm install currypp

    The tests skip source compilation when the tool is absent and can use
    the precompiled products in the test archives. The benchmark harness
    records these programs as excluded, with the missing tool as the reason.

Python
    Sprite supports Python 3.11 to 3.15, with 3.11.4 as the minimum because
    archive extraction uses ``tarfile.extractall(filter=)``.  CMake
    rejects older versions.  Python 3.14 remains the development default.
    CI runs the C++ unit suites on each version, and every lane gates the
    job: 3.11 to 3.15, and the free-threaded 3.14t without the GIL
    (``PYTHON_GIL=0``), green since 2026-10-18.  Children inherit
    ``PYTHON_GIL`` when set.

..
  Sources
  =======

  - Python is available through most software package managers.  For fine control
    over the version on Ubuntu, consider using the `deadsnakes PPA
    <https://github.com/deadsnakes>`_.  To build from source, download Python
    `here <https://www.python.org/downloads/>`__.

  - Prolog is available `here <https://www.swi-prolog.org>`__.  It is a
    prerequisite of PAKCS.

  - Download PAKCS `here <https://www.curry-lang.org/pakcs/>`__.

  - The ICurry Compiler (optional) is available through the `Curry Package
    Manager`_.  After installing PAKCS, say the following from your home
    directory:

    .. code:: bash

        cypm update
        cypm add icurry

  - `pybind11 <https://github.com/pybind/pybind11>`_ is automatically cloned into
    Sprite via the ``git submodules`` command the first time ``make`` is run.


  .. _Curry Package Manager: https://www.curry-lang.org/tools/cpm/

Search library
    ``Control.SetFunctions`` remains Sprite's extension.
    ``Control.Search.SetFunctions``, ``Control.Search.Unsafe``, and
    ``Control.Search.AllValues`` are supported over its native capsules.
    The two set-function modules share ``Values a = Values [a]``, preserve
    multiplicities, capture body choices, and leave argument choices outside.
    Strategies and DFS names are advisory: Sprite uses its fair scheduler
    and its own value order. ``getSomeValue`` and ``getSome`` select in IO.

    Upstream Unsafe and AllValues describe strong encapsulation, enumerating
    free variables inside an expression. Sprite provides weak encapsulation:
    free variables are not enumerated inside and can demand outside bindings.
    ``rewriteAll`` and ``rewriteSome`` report not implemented at the call,
    since capsules cannot discard computations that demand such bindings.
    ``Control.Search.SearchTree`` remains unsupported; strong search is
    future work.
