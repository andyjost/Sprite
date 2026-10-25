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
``WITH_CURRY_FRONTEND``         Front end 2.0.0 or 3.1.0; ``AUTO`` searches PAKCS and PATH
``WITH_PAKCS``                  Optional oracle 3.4.1 or 3.10.0; ``AUTO`` searches PATH
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

The standalone front-end package
--------------------------------

The platform wheel ``curry-frontend`` installs the command
``curry-frontend`` and needs no Haskell tools at run time. The wheels that
the front-end CI workflow builds are artifacts for review; they are not
published to PyPI. Install the wheel for your platform, then configure
Sprite without PAKCS::

    python -m pip install /path/to/curry_frontend-2.0.0.postN-py3-none-PLATFORM.whl
    cmake -S . -B object-root/cmake -G Ninja -DWITH_PAKCS= -DWITH_CURRY_FRONTEND=curry-frontend
    make stage

``WITH_CURRY_FRONTEND`` accepts a command on PATH or a path to an
executable. With ``AUTO``, the default, the configuration takes
``SPRITE_FRONTEND`` from the environment when it is set, and otherwise
searches the directory of the selected PAKCS, the staged ``install/tools``
and PATH for ``pakcs-frontend`` or ``curry-frontend``. The older variable
``CURRY_FRONTEND`` sets the default of the option. The installed
``tools/curry-frontend`` link points to the selected executable, a wheel's
console script included.

At run time ``SPRITE_FRONTEND`` overrides that link; it may name a command
on PATH. If the link is absent, Sprite searches PATH for ``curry-frontend``,
then ``pakcs-frontend``. An empty ``SPRITE_FRONTEND`` disables the front
end. For example::

    export SPRITE_FRONTEND=curry-frontend
    python -m curry.tools.icy

The supported pairs are front end ``2.0.0`` with PAKCS ``3.4.1`` (the
default) and front end ``3.1.0`` with PAKCS ``3.10.0``. The current
front-end wheel is ``3.1.0.post1``; substitute it in the command above to
select that pair. CMake derives the intermediate directory names and CPP
flags from the selected front end and rejects a mismatched oracle.
The default stays on 2.0.0/3.4.1 until upgrade stage G. The wheel's
``.postN`` suffix counts packaging revisions.

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
