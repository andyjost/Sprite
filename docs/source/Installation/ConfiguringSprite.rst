.. highlight:: bash

Configuring Sprite
==================

Sprite uses CMake 3.24 or newer, Ninja, a C++17 compiler and Python 3.11.4
or newer. The build uses vendored pybind11. CMake, Ninja and Python come
from the active environment, whether conda or the system. Select a clean
environment when another toolchain has exported compiler flags.

Check prerequisites without changing the machine::

    make check-prereqs
    python scripts/check-prereqs.py --doc

Configure the build, then stage the traditional installation::

    cmake -S . -B object-root/cmake -G Ninja \
      -DPython_EXECUTABLE="$(command -v python3)" \
      -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
      -DWITH_CURRY_FRONTEND=/path/to/pakcs-frontend
    make stage

``make stage`` configures the build if needed, builds it and installs into
``install/``. It preserves settings in ``object-root/cmake/CMakeCache.txt``.
Use ``cmake -LAH -N object-root/cmake`` to inspect them.

The options
-----------

==============================  ============================================================
Option                          Meaning and default
==============================  ============================================================
``WITH_CURRY_FRONTEND``         Front end 2.0.0; ``AUTO`` searches PAKCS and PATH
``WITH_PAKCS``                  Optional oracle 3.4.1; ``AUTO`` searches PATH
``WITH_ICURRY``                 Optional translator; empty by default
``CURRY2ICURRY_TOOL``           ``frontend`` (default) or ``icurry``
``WITH_CCACHE``                 Compiler launcher; empty disables it (default)
``WITH_CXX_POSTINSTALL``        Compiler for generated modules; the build compiler
``WITH_DEFAULT_BACKEND``        ``cxx`` (default); see Developer Notes
``GC``                          ``wdgc`` (default) or ``mps``
``CMAKE_BUILD_TYPE``            ``Release`` (default) or ``Debug``
``JOBS``                        Library parallelism; ``auto`` (default) or a count
``TRACE``                       Computation tracing; ``OFF``
``COUNTERS``                    Scheduler counters; ``OFF``
``GC_WRITE_COUNTERS``           Old-node write counters with wdgc; ``OFF``
``SPRITE_REBUILD_ICY``          Rebuild pinned ICurry; ``OFF``
``ENABLE_ICURRY_CACHE``         Enable the user ICurry cache by default; ``OFF``
``ENABLE_PARSED_JSON_CACHE``    Cache parsed JSON by default; ``OFF``
==============================  ============================================================

Pass each setting as ``-DNAME=value``. An empty ``WITH_PAKCS`` disables the
oracle. Both translation routes require the Curry front end at build time.
The MPS collector needs the ``extern/mps`` submodule. CMake honours ``CC``,
``CXX``, ``CFLAGS``, ``CXXFLAGS`` and ``LDFLAGS`` on its first configuration.
Standard CMake compiler and flag options override those defaults.

For a parallel developer build with ccache::

    make stage CMAKE_ARGS=-DWITH_CCACHE=ccache

``make stage JOBS=4`` or ``make -j4 stage`` limits native compilation and
the library build. An explicit ``-j`` wins over ``JOBS``.

Wheels
------

The distribution is ``currylang``; its Python package is ``curry``::

    python -m pip wheel .
    python -m pip install .

The scikit-build-core backend builds the same native targets and library.
Release builds use pip build isolation. A development environment with
scikit-build-core already installed can use ``--no-build-isolation``.
The installed package has no new runtime Python dependencies. Running its
shipped modules needs no front end. Compiling Curry source searches
``SPRITE_FRONTEND``, the package's tools directory and PATH; a missing
front end produces an error at that compile.
