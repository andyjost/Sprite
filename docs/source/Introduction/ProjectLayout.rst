Project Layout
==============

The repository contains these sources and generated trees:

``CMakeLists.txt``, ``pyproject.toml``
    The native build and the scikit-build-core wheel metadata. ``make stage``
    configures, builds and installs; its CMake cache is under ``object-root``.

``Makefile``, ``AGENTS.md``, ``CONTRIBUTING.md``, ``LICENSE``
    The build wrapper, project instructions, contribution guide and license.

``README.md``, ``README.pypi.md``, ``VERSION``
    The README of the repository, the page of the PyPI distribution, and
    the version of the distribution.

``assets/``
    The logo: the mark, the wordmark, the lockup, the palette and the
    generator.  ``assets/logo/README.md`` describes them.

``conda/``
    The scaffold of a conda package: a recipe for Sprite and one for the
    Curry front end.  ``conda/README.md`` describes them and what remains
    open.  Nothing is published.

``contrib/``
    Editor support outside the package: ``vim/syntax/spritelog.vim`` and its
    ``ftdetect`` file highlight the computation traces of a runtime built
    with ``TRACE=ON``.

``curry/``
    The built-in Curry library.  ``curry/lib/`` holds the sources: a copy of
    the library of the pinned PAKCS release, Sprite's own modules, the license
    of the origin and the pinned ICurry products.  See ``curry/README.md``.

``docs/``
    The Sphinx sources. After ``make stage``, ``make -C docs html`` builds
    HTML into ``object-root/docs/html`` (:doc:`/DeveloperSetup`).

``examples/``
    The numbered lessons (:doc:`/Examples`).

``extern/``
    External projects used by Sprite, as Git submodules: ``pybind11`` and
    ``libtommath`` are needed by the build, ``mps`` by the optional
    collector.  Run ``git submodule update --init extern/pybind11
    extern/libtommath`` before the first build.

``frontend/``
    The packaging of the Curry front end as the distribution
    ``curry-frontend``: the build script, the source and compiler pins, the
    patches and the parity check.  ``frontend/README.md`` describes it.

``getsprite``, ``getsprite-i``
    The one-line installers; see :doc:`/Installation/Installation`.

``scripts/``
    Scripts called by the build: ``build-package.py``, ``install-package.py``,
    ``overlay.py`` and ``check-prereqs.py``. Also ``library_pins.py``,
    ``new-worktree.sh``, wheel checks under ``wheels/`` and
    ``setup-dev-machine.sh`` (:doc:`/DeveloperSetup`).

``src/``
    The Sprite source code.

    ``export/``
        Files exported to the installation directory.

    ``python/``
        The Python code implementing Sprite.

    ``curryrt/``
        Source code of the Sprite runtime libraries.

``tests/``
    The test suite.  See ``tests/README`` for help running tests.

    ``data/``
        The test data. This includes Curry source files, text (data) files, and
        expected results.

    ``func_*.py``
        Functional tests.  These run whole Curry programs and check their
        output against another Curry system.

    ``lib/``
        Test support code.  The ``cytest`` subdirectory contains useful
        extensions to Python's ``unittest`` module for testing Curry programs.

    ``oracle*``
        Driver scripts for Curry oracles.  An oracle is a Curry system such as
        PAKCS or KiCS2 that generates the expected output of a Curry program.
        Functional tests validate Sprite by comparing its output to that of an
        oracle.

    ``run_tests``
        The test driver.  Used to run tests.

    ``unit_*.py``
        Unit tests.  These test isolated components of Sprite.




    ``overlay/``
        The overlay archives, one per supported version of PAKCS: the prebuilt
        ICurry and FlatCurry files of the test programs.  Run ``make overlay`` to
        apply the overlay.
        The archive also holds the FlatCurry interfaces of the Curry library.
        The oracle tests of the FlatCurry-to-ICurry port read them; see
        :ref:`compilation-pipeline`.  The ICurry products of the library itself
        are committed under ``curry/lib``.

.. _install-tree-layout:

``install/`` (dynamically created)
    The staged installation that ``make stage`` writes; the tests and
    documentation build read it. Delete it to remove the staged tree.
    ``make install`` follows the same layout.

    ``bin/``
        Executable files installed by Sprite.

    ``curry/``
        The built-in Curry library.  Sprite automatically adds this to the end
        of the search path used to locate Curry modules.

    ``include/``
        The headers of the runtime, which the generated code of a module
        includes.

    ``lib/``
        The Sprite runtime libraries.  The contents of this directory are
        needed to run programs compiled by Sprite.

    ``licenses/``
        The licenses of the vendored components.

    ``python/``
        The Sprite Python API.  Contains the code loaded by the Python
        statement ``import curry``.

    ``sysconfig/``
        System variables set during configuration.

    ``tools/``
        Links to external programs used by Sprite.

``object-root/`` (dynamically created)
    Build products: the CMake cache, object files, libraries and built
    documentation. Delete it for a clean build.


Python package structure
========================

The modules under ``src/python/`` implement the ``curry`` package.
:doc:`/PythonAPI/UsingTheAPI` describes its public surface. Internal
modules include:

``backends/``
    The ``IBackend`` interface, its ``cxx`` implementation and shared code.
``cache.py``
    The cache of the Curry-to-ICurry step.
``common.py``, ``config.py``, ``exceptions.py``
    Shared definitions, installation configuration and public exceptions.
``icurry/``
    The Python classes of ICurry, the intermediate language of the compiler.
``inspect/``
    Predicates and metadata access for modules, terms and generated code.
``interpreter/``
    Sessions, flags and the operations behind the top-level API.
``lib/``
    The import hook for Curry modules.
``objects/``
    Modules, terms and converted values returned by the public API.
``show.py``
    Conversion of Curry values to text.
``toolchain/``
    The :ref:`compilation pipeline <compilation-pipeline>` and external tools.
``tools/``
    :ref:`sprite-make` and the :ref:`REPL <repl>`; :ref:`sprite-exec` lives
    in ``__main__.py``.
``typecheck/``
    The typed boundary: schemes, defaulting, goals, ``engine``, ``builder``
    and the type-error catalog.
``utility/``
    General-purpose code.
