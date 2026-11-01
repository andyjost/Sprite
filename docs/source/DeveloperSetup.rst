===============
Developer Setup
===============

This page sets up a machine for work on Sprite itself.  One script does the
work: ``scripts/setup-dev-machine.sh``.  It puts every bulky product under
one scratch prefix, builds the pinned toolchain, configures and stages
Sprite and runs a smoke test.  The script never runs ``sudo``.  When an apt
package is missing, it prints the apt command and stops.

Run the script
==============

Clone the repository, print the plan, then run it::

    git clone https://github.com/andyjost/Sprite.git
    cd Sprite
    scripts/setup-dev-machine.sh --prefix /path/to/scratch --dry-run
    scripts/setup-dev-machine.sh --prefix /path/to/scratch

The dry run prints every command and runs none.  The real run stops at the
first problem.  Fix the cause, then run the same command again: a finished
step is skipped and CMake runs again only when its flags changed or
``--reconfigure`` asks for it.  The whole run takes under an hour on a
current machine.  Most of that time goes to the PAKCS build, the conda
solve and the compilation of the Curry library for the runtime.

The default toolchain is PAKCS 3.10.0 with front end 3.1.0. To select
PAKCS 3.4.1 with front end 2.0.0, using its pinned archive checksum::

    PAKCS_VERSION=3.4.1 scripts/setup-dev-machine.sh --prefix /path/to/scratch --dry-run
    PAKCS_VERSION=3.4.1 scripts/setup-dev-machine.sh --prefix /path/to/scratch

Both pairs are supported; see :doc:`Installation/SoftwareCompatibility`.
The script uses the front end shipped by the selected PAKCS. A build
without PAKCS or a front end uses the pinned library products; see
:doc:`Installation/ManualInstallation`.

The steps
=========

The script runs nine steps in this order.

1. Machine.  Prints the OS, the cores, the memory, the swap and the tools
   it found.  ``--jobs auto`` stays ``auto``: ``make`` counts the
   processors when it starts, so no count of this machine enters
   ``CMakeCache.txt``.
2. apt packages.  Checks ``git swi-prolog-nox g++ make curl ccache time``
   and the ``linux-tools`` packages of the running kernel, which provide
   ``perf``.  SWI-Prolog serves PAKCS alone: the build of its saved states
   in step 3 and the test oracle ``pakcs``.  Sprite itself runs no Prolog,
   and its C++ runtime needs no Boost.  ``time`` is GNU time, which the
   benchmark harness uses for the peak memory of a run.  A missing package
   stops the script.  The printed command installs the missing ones.
   ``--skip-apt`` skips the check on a system without dpkg.
3. PAKCS 3.10.0.  Downloads the binary archive from curry-lang.org into
   ``PREFIX/downloads`` and verifies its SHA-256.  The hash is pinned in the script.  The archive unpacks to
   ``PREFIX/pakcs-3.10.0``. The script runs ``make`` there. For the legacy
   release it also extends the SWI-Prolog 8 stack-limit setting to version 9.
   The build takes about five minutes.  Sprite takes the Curry front end
   and the test oracle from this tree.
4. Checkout.  Clones the repository when ``--repo`` names a missing
   directory.  Initializes the ``pybind11`` and ``libtommath`` submodules.  Links ``install``
   and ``object-root`` of the checkout to ``PREFIX/install`` and
   ``PREFIX/object-root``.  A link that points elsewhere stops the script.
   The script deletes nothing.
5. Conda environment.  Creates ``PREFIX/conda/env`` from
   ``conda/dev-environment.yml`` of the checkout with micromamba, mamba,
   or conda, whichever is found first.  The package cache goes to
   ``PREFIX/conda/pkgs``.  The environment holds Python 3.14, numpy,
   Sphinx, its theme, CMake, Ninja, scikit-build-core and python-build.
6. Configure. Runs CMake with Ninja, the system compilers, the PAKCS of
   step 3 and the Python of step 5. CMake, Ninja and scikit-build-core come
   from the environment, conda or the system. The script puts the conda
   environment's tools first on PATH and selects the native compilers
   explicitly. It records flags in ``PREFIX/cmake-args`` and skips
   configuration while ``object-root/cmake/CMakeCache.txt`` exists and
   the flags agree. ``--reconfigure`` reruns CMake without deleting products.
7. ``make stage``.  Builds the runtime and compiles the Curry library for
   the C++ runtime.  Then ``make overlay`` extracts the archived products of
   the test programs, after the stage so that they are newer than the
   installed library interfaces.
8. Smoke test.  Runs one fast unit test file on the runtime under the
   address-space cap and the time limit of the test drivers.
9. Next steps.  Prints the paths to record and the runs
   to make next.

With ``--icurry`` the script also installs ``icurry`` 3.3.0 through the
Curry Package Manager, after step 3.  That is the optional second route
from Curry to ICurry.  It writes ``~/.cpmrc``
only when the file is missing, with the Curry Package Manager home under ``PREFIX/cpm``.

The clean environment
=====================

A conda toolchain in the login shell exports ``CC``, ``CXX``, ``CFLAGS``,
``CXXFLAGS``, ``CPPFLAGS`` and ``LDFLAGS``.  CMake honors those flags, so a build in that shell mixes two toolchains.  The
script runs CMake, make and the smoke test under ``env -i`` with five
variables: ``PATH=PREFIX/conda/env/bin:/usr/local/bin:/usr/bin:/bin``, ``HOME``,
``LC_ALL=C.UTF-8``, ``TMPDIR`` and ``CCACHE_DIR=PREFIX/ccache``.  Use the
same command for every later build::

    env -i PATH=PREFIX/conda/env/bin:/usr/local/bin:/usr/bin:/bin HOME=$HOME LC_ALL=C.UTF-8 CCACHE_DIR=PREFIX/ccache make stage

``CXXFLAGS`` in the environment adds to the flags of the build and the
generated code; it cannot remove one.

``CCACHE_DIR`` keeps the compiler cache under the prefix, not under
``HOME``.  With ``-DWITH_CCACHE=ccache`` the compiler of the
installation runs ccache too, so every test and every program that
compiles a module for the runtime reads the variable.  For a shell
outside the clean environment, run
``ccache --set-config cache_dir=PREFIX/ccache``.
``SPRITE_SETUP_CLEAN_PATH`` replaces the PATH of the clean environment.

Layout of the prefix
====================

================================  ==============================================
Path                              Content
================================  ==============================================
``PREFIX/downloads``              the PAKCS archive
``PREFIX/pakcs-3.10.0``           PAKCS: ``bin/pakcs``, ``bin/pakcs-frontend``,
                                  ``bin/cypm``
``PREFIX/conda/env``              the conda environment; ``bin/python`` is the
                                  Python of Sprite
``PREFIX/conda/pkgs``             the conda package cache
``PREFIX/install``                the staged installation, linked from the checkout
``PREFIX/object-root``            the object tree, linked from the checkout
``PREFIX/cpm``                    the CPM home, with ``--icurry``
``PREFIX/ccache``                 the compiler cache (``CCACHE_DIR`` of the
                                  clean environment)
``PREFIX/cmake-args``             the flags of the last CMake configuration
================================  ==============================================

Options
=======

===================  =========================================================
Option               Meaning
===================  =========================================================
``--prefix DIR``     the scratch root; required
``--repo DIR``       the checkout; cloned when missing; the default is the
                     checkout that holds the script
``--repo-url URL``   the clone URL
``--branch NAME``    the branch to clone
``--jobs N|auto``    the job count for CMake and the Curry library; auto is
                     one job per processor
``--reconfigure``    rerun CMake although its cache exists and the flags
                     are the ones of the last run
``--dry-run``        print every command, run none
``--skip-apt``       do not check the apt packages
``--icurry``         also install icurry 3.3.0 through cypm
``--smoke-file F``   the unit test file of the smoke test; the default is
                     ``unit_expr.py``
``--cap-kb N``       the address-space cap of each smoke run in KiB, or
                     ``unlimited``; the default is the cap of
                     ``tests/run_tests``
``--timeout SEC``    the time limit of each smoke run
``--cc``, ``--cxx``  the system compilers
===================  =========================================================

``PAKCS_VERSION`` and ``ICURRY_VERSION`` in the environment change the
pinned versions.  A PAKCS version without a pinned hash gets its size and
hash printed instead of a check.

Every budget is a parameter: the job count, the memory cap and the time
limit.  The script detects the cores and the memory and prints them.  Do
not copy a number from one machine to the next.

After the setup
===============

The last step prints the same list with the paths of the machine.

1. Calibrate the test manifest on the new machine.  Run every test file
   once on a quiet machine with the manifest update of the test runner,
   after the prepare pass, so that the durations exclude it::

       cd tests
       ./run_tests --prepare-only
       ./run_tests -j 1 --update-manifest

   This calibrates the runner for this machine. Commit ``tests/manifest.json``
   only when maintaining the calibration machine.  See ``./run_tests -h``
   and section 10 of ``tests/README``.
2. Record a baseline with the benchmark harness on a quiet machine.  The
   records carry the deterministic columns steps, forks and collections,
   which the compare command checks::

       cd tests
       ./run_benchmarks -b cxx --label baseline -o PREFIX/baseline.jsonl
       ./run_benchmarks counters PREFIX/baseline.jsonl

3. Record the new paths in your own notes: the Python, the
   PAKCS tree, icurry, the installation and object trees, the conda package
   cache, the compiler cache and the clean environment.  Record the cores
   and the memory.
4. Copy ``tests/.cache/icurry.db`` from the old machine.  The cache is
   keyed by the source text, so the first suite run then compiles nothing.

Notes
=====

- The Kiel mirrors of the Curry Package Manager do not answer.  The script
  writes a ``~/.cpmrc`` that names ``cpm.curry-lang.org``.
- The script was written for Ubuntu 24.04.  On another distribution,
  install the equivalents of the apt packages and pass ``--skip-apt``.
- ``tests/unit_setup_script.py`` runs the script with ``--dry-run`` and
  checks the plan.  It needs no network and installs nothing.

Building by hand
================

Without the script, build as :doc:`Installation/ConfiguringSprite` describes.
In a conda environment keep the system compiler
(``-DCMAKE_CXX_COMPILER=/usr/bin/g++``) and put the environment's tools
first on PATH.

.. _starting-python:

The staged Python
=================

The staged installation has a ``python`` wrapper, ``install/bin/python``,
that starts the Python of the build with ``curry`` importable. A pip
installation uses the Python that installed the package. After
``make stage``, start the wrapper::

    install/bin/python

A script whose first line is ``#!/path/to/sprite/bin/python`` uses the
wrapper too.

.. _sprite-invoke:

``sprite-invoke`` runs a command in the installation's environment, where
the runtime library is found. With a shell it shows that environment::

    sprite-invoke $SHELL

The wrapper uses ``sprite-invoke`` to start the Python selected during
configuration, linked at ``install/tools/python``. The compiled bindings
require that Python. To start it under gdb::

    sprite-invoke gdb install/tools/python

Building the documentation
==========================

The user guide of ``master`` is published at
https://andyjost.github.io/Sprite/. To build the guide of your checkout,
stage the package and run Sphinx through the wrapper::

    make stage
    python scripts/check-prereqs.py --doc
    make -C docs html

Install Sphinx and sphinx_rtd_theme in the build Python's environment when
the diagnostic reports them missing. The wrapper regenerates the Reference
from the installed package and command help from the staged tools, then
builds HTML with warnings treated as errors. The output is
``object-root/docs/html``. ``make docs`` builds HTML and then PDF (which also needs TeX).

After removing Reference source pages, clear the old output first::

    make -C docs clean
    make -C docs html

.. _spritelog-highlighting:

Trace logs
==========

A runtime built with ``make stage TRACE=1`` writes computation traces.
The trace log has its own Vim syntax, ``spritelog``. Copy
``contrib/vim/syntax/spritelog.vim`` to ``~/.vim/syntax/`` and
``contrib/vim/ftdetect/spritelog.vim`` to ``~/.vim/ftdetect/``. The second
file holds one line:

.. code-block:: vim

    au BufRead,BufNewFile *spritelog set filetype=spritelog
