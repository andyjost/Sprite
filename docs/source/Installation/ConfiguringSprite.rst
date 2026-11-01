Building From Source
====================

Sprite uses CMake 3.24 or newer, Ninja, a C++17 compiler and Python 3.11.4
or newer. The build uses the pybind11 submodule. CMake, Ninja and Python come
from the active environment, whether conda or the system. Select a clean
environment when another toolchain has exported compiler flags.

Check prerequisites without changing the machine::

    make check-prereqs
    python scripts/check-prereqs.py --doc

.. _easy-build:

Build, stage and test
---------------------

Initialize the two submodules the build needs::

    git submodule update --init extern/pybind11 extern/libtommath

Stage the installation with the thin CMake wrapper::

    make stage

This configures ``object-root/cmake`` with Ninja, builds the runtime and
bindings, prepares the Curry library and installs into ``install/``.
It preserves the flags in ``object-root/cmake/CMakeCache.txt``.
Use ``cmake -LAH -N object-root/cmake`` to inspect them.

Extract the test products after staging, then run the tests::

    make overlay
    cd tests
    ./run_tests --prepare-only
    ./run_tests

A plain ``make`` stages and then extracts the overlay. ``make test`` runs
the full suite; its functional tests need PAKCS on PATH or selected with
``-DWITH_PAKCS=PATH``. ``tests/README`` describes the overlay archives and
the oracle.

To install the prepared tree elsewhere::

    cmake --install object-root/cmake --prefix /path/to/sprite

``make install PREFIX=/path/to/sprite`` also builds first. See the
:ref:`install tree layout <install-tree-layout>` for the resulting tree.

The options
-----------

==============================  ============================================================================
Option                          Meaning and default
==============================  ============================================================================
``WITH_CURRY_FRONTEND``         Front end 3.1.0 (legacy 2.0.0); ``AUTO`` searches PAKCS and PATH
``WITH_PAKCS``                  Optional oracle 3.10.0 (legacy 3.4.1); ``AUTO`` searches PATH
``WITH_ICURRY``                 Optional translator; empty by default
``CURRY2ICURRY_TOOL``           ``frontend`` (default) or ``icurry``
``WITH_CCACHE``                 Compiler launcher; empty disables it (default)
``WITH_CXX_POSTINSTALL``        Compiler for generated modules; the build compiler
``GC``                          ``wdgc`` (default) or ``mps``
``CMAKE_BUILD_TYPE``            ``Release`` (default) or ``Debug``
``JOBS``                        Library parallelism; ``auto`` (default) or a count
``TRACE``                       Computation tracing; ``OFF``
``COUNTERS``                    Scheduler counters; ``OFF``
``GC_WRITE_COUNTERS``           Old-node write counters with wdgc; ``OFF``
``SPRITE_REBUILD_ICY``          Rebuild pinned ICurry; ``OFF``
``ENABLE_ICURRY_CACHE``         Enable the user ICurry cache by default; ``OFF``
``WITH_CLANG``                  clang++ for the bitcode of the JIT helpers; ``AUTO`` finds one on PATH, empty disables
``WITH_CLANG_FLAGS``            Extra flags for that clang; empty (default)
==============================  ============================================================================

Pass each setting as ``-DNAME=value``. ``-DPython_EXECUTABLE=PATH`` selects
the Python of the build and ``-DCMAKE_CXX_COMPILER=PATH`` the compiler. CMake
rejects a PAKCS whose version does not match the selected front end. An
empty ``WITH_PAKCS`` disables the oracle. A build needs no front end: CMake builds the library from the
pinned products. The front end is needed at run time for new Curry text, and
when ``SPRITE_REBUILD_ICY`` rebuilds the pins.
The MPS collector needs the ``extern/mps`` submodule. CMake honors ``CC``,
``CXX``, ``CFLAGS``, ``CXXFLAGS`` and ``LDFLAGS`` on its first configuration.
Standard CMake compiler and flag options override those defaults.

For a parallel developer build with ccache::

    make stage CMAKE_ARGS=-DWITH_CCACHE=ccache

``make stage JOBS=4`` or ``make -j4 stage`` limits native compilation and
the library build. An explicit ``-j`` wins over ``JOBS``.

The standalone front end package
--------------------------------

The platform wheel ``curry-frontend`` installs the command
``curry-frontend`` and needs no Haskell tools at run time.
Install the package, then configure Sprite without PAKCS::

    pip install curry-frontend
    cmake -S . -B object-root/cmake -G Ninja -DWITH_PAKCS= -DWITH_CURRY_FRONTEND=curry-frontend
    make stage

``WITH_CURRY_FRONTEND`` accepts a command on PATH or a path to an
executable. With ``AUTO``, the default, the configuration takes
``SPRITE_FRONTEND`` from the environment when it is set and otherwise
searches the directory of the selected PAKCS, the staged ``install/tools``
and PATH for ``pakcs-frontend`` or ``curry-frontend`` of the matching
version. Without an explicit selection, AUTO finds only the current pair. The older variable
``CURRY_FRONTEND`` sets the default of the option. The installed
``tools/curry-frontend`` link points to the selected executable, a wheel's
console script included.

At run time ``SPRITE_FRONTEND`` wins; an empty value disables the front
end. Next comes the installed ``tools/curry-frontend`` link, then the
``curry-frontend`` script beside the Python interpreter, then
``curry-frontend`` and ``pakcs-frontend`` on PATH. For example::

    SPRITE_FRONTEND=curry-frontend python -m curry

Wheels
------

The distribution is ``curry``; its Python package is ``curry``::

    pip wheel .
    pip install .

The scikit-build-core backend builds the same runtime, bindings and library.
Release builds use pip build isolation. A development environment with
scikit-build-core already installed can use ``--no-build-isolation``.
The installed package depends on ``curry-frontend`` at run time, and on
``llvmlite`` for the LLVM JIT except on Intel macOS, where conda-forge
provides it. Running its shipped modules needs no front end. Compiling Curry source searches
``SPRITE_FRONTEND``, the package's tools directory and PATH; a missing
front end produces an error at that compile.
