
Project Layout
==============

The Sprite repository is organized as follows:

``assets/``
    The logo: the mark, the wordmark, the lockup, the palette and the
    generator.  ``assets/logo/README.md`` describes them.

``conda/``
    The scaffold of a conda package: a recipe for Sprite and one for the
    Curry front end.  ``conda/README.md`` describes them and what remains
    open.  Nothing is published.

``CMakeLists.txt``, ``pyproject.toml``
    The native build and the scikit-build-core wheel metadata. ``make stage``
    configures, builds and installs; its CMake cache is under ``object-root``.

``README.md``, ``README.pypi.md``, ``VERSION``
    The README of the repository, the page of the PyPI distribution, and
    the version of the distribution.

``getsprite``, ``getsprite-i``
    The one-line installers; see :doc:`../Installation/EasyInstallation`.

``curry/``
    The built-in Curry library.  ``curry/lib/`` holds the sources: a copy of
    the library of the pinned PAKCS release, Sprite's own modules, the license
    of the origin, and the pinned ICurry products.  See ``curry/README.md``.

``docs/``
    Files used to build documentation.  Say ``cd docs &&
    make html`` to build HTML documentation.

``examples/``
    Examples demonstrating Sprite.

``extern/``
    External projects used by Sprite, as Git submodules: ``pybind11`` and
    ``libtommath`` are needed by the build, ``mps`` by the optional
    collector.  Run ``git submodule update --init extern/pybind11
    extern/libtommath`` before the first build.

.. _install-tree-layout:

``frontend/``
    The packaging of the Curry front end as the distribution
    ``curry-frontend``: the build script, the source and compiler pins, the
    patches and the parity check.  ``frontend/README.md`` describes it.

``install/`` (dynamically created)
    The staging area created by the ``make stage`` command.  Sprite is
    installed here for use in testing and building help documents.  It is safe
    to remove this directory.

    The installation tree created by ``make install`` also follows this layout.

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
    The directory containing all build products such as object files,
    libraries, and help documents.  It is safe to remove this directory, for
    instance, to reclaim disk space or prepare for a clean build.

``tests/overlay/``
    The overlay archives, one per supported version of PAKCS: the prebuilt
    ICurry and FlatCurry files of the test programs.  Say ``make overlay`` to
    apply the overlay.
    The archive also holds the FlatCurry interfaces of the Curry library.
    The oracle tests of the FlatCurry-to-ICurry port read them; see
    :ref:`compilation-pipeline`.  The ICurry products of the library itself
    are committed under ``curry/lib``.

    .. warning::
       It is important to choose a version
       of PAKCS that matches one of the overlay files, as it reduces the time
       required to run tests from several hours to just a few minutes.  Applying
       the overlay avoids having to compile hundreds of test modules to ICurry.

``scripts/``
    ``setup-dev-machine.sh``, the script that sets up a machine for work
    on Sprite; see :doc:`/DeveloperSetup`.

``contrib/``
    Editor support outside the package: ``vim/syntax/spritelog.vim`` and its
    ``ftdetect`` file highlight the computation traces of a runtime built
    with ``TRACE=ON``.

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
        Functional tests.  These execute whole Curry programs and check their
        output against another Curry system.

    ``lib/``
        Test support code.  The ``cytest`` subdirectory contains useful
        extensions to Python's ``unittest`` module for testing Curry programs.

    ``oracle*``
        Driver scripts for Curry oracles.  An oracle is a Curry system such as
        PAKCS or KiCS2 that generates the expected output a Curry program.
        Functional tests validate Sprite by comparing its output to that of an
        oracle.

    ``run_tests``
        The test driver.  Used to run tests.

    ``unit_*.py``
        Unit tests.  These test isolated components of Sprite.


