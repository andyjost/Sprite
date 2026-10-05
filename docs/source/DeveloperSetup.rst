.. highlight:: bash

===============
Developer Setup
===============

This page sets up a machine for work on Sprite itself.  One script does the
work: ``scripts/setup-dev-machine.sh``.  It puts every bulky product under
one scratch prefix, builds the pinned toolchain, configures and stages
Sprite, and runs a smoke test.  The script never runs ``sudo``.  When an apt
package is missing, it prints the apt command and stops.

Quick start
===========

Clone the repository, print the plan, then run it::

    git clone https://github.com/andyjost/Sprite.git
    cd Sprite
    scripts/setup-dev-machine.sh --prefix /path/to/scratch --dry-run
    scripts/setup-dev-machine.sh --prefix /path/to/scratch

The dry run prints every command and runs none.  The real run stops at the
first problem.  Fix the cause, then run the same command again: a finished
step is skipped, and configure runs again only when its flags changed or
``--reconfigure`` asks for it.  The whole run takes under an hour on a
current machine.  Most of that time goes to the PAKCS build, the conda
solve, and the compilation of the Curry library for the C++ backend.

The steps
=========

The script runs nine steps in this order.

1. Machine.  Prints the OS, the cores, the memory, the swap, and the tools
   it found.  ``--jobs auto`` stays ``auto``: ``make`` counts the
   processors when it starts, so no count of this machine enters
   ``Make.config``.
2. apt packages.  Checks ``git swi-prolog-nox g++ make libboost-dev curl
   ccache time`` and the ``linux-tools`` packages of the running kernel,
   which provide ``perf``.  A missing package stops the script.  The
   printed command installs the missing ones.  ``--skip-apt`` skips the
   check on a system without dpkg.
3. PAKCS 3.4.1.  Downloads the binary archive from curry-lang.org into
   ``PREFIX/downloads`` and verifies its SHA-256.  The hash is the one of
   ``conda/curry-frontend/meta.yaml``.  The archive unpacks to
   ``PREFIX/pakcs-3.4.1``.  The script gives SWI-Prolog 9 the stack limit
   that the distribution sets for version 8, then runs ``make`` there.
   The build takes about five minutes.  Sprite takes the Curry front end
   and the test oracle from this tree.
4. Checkout.  Clones the repository when ``--repo`` names a missing
   directory.  Initializes the pybind11 submodule only.  Links ``install``
   and ``object-root`` of the checkout to ``PREFIX/install`` and
   ``PREFIX/object-root``.  A link that points elsewhere stops the script.
   The script deletes nothing.
5. Conda environment.  Creates ``PREFIX/conda/env`` from
   ``conda/dev-environment.yml`` of the checkout with micromamba, mamba,
   or conda, whichever is found first.  The package cache goes to
   ``PREFIX/conda/pkgs``.  The environment holds Python 3.14, numpy,
   Sphinx, and the Sphinx theme, and nothing else.
6. configure.  Runs ``configure`` in the clean environment with the system
   compilers, the PAKCS of step 3, and the Python of step 5.  The script
   probes ``configure --help`` and adds ``--jobs`` and ``--with-ccache``
   when configure supports them.  configure empties ``install`` and
   ``object-root``, so the script records the flags in
   ``PREFIX/configure-args`` and skips the step while ``Make.config``
   exists and the flags are the same.  ``--reconfigure`` forces it.
7. ``make stage``.  Builds the runtime and compiles the Curry library for
   both backends.
8. Smoke test.  Runs one fast unit test file on each backend under the
   address-space cap and the time limit of the test drivers.
9. Next steps.  Prints the paths for the personal rules file and the runs
   to make next.

With ``--icurry`` the script also installs ``icurry`` 3.1.0 through the
Curry Package Manager, after step 3.  That is the optional second route
from Curry to ICurry.  The step follows the CI script
``.github/scripts/install-curry-toolchain.sh``.  It writes ``~/.cpmrc``
only when the file is missing, with the CPM home under ``PREFIX/cpm``.

The clean environment
=====================

A conda toolchain in the login shell exports ``CC``, ``CXX``, ``CFLAGS``,
``CXXFLAGS``, ``CPPFLAGS``, and ``LDFLAGS``.  The Makefiles of Sprite
append those flags, so a build in that shell mixes two toolchains.  The
script runs configure, make, and the smoke test under ``env -i`` with five
variables: ``PATH=/usr/local/bin:/usr/bin:/bin``, ``HOME``,
``LC_ALL=C.UTF-8``, ``TMPDIR``, and ``CCACHE_DIR=PREFIX/ccache``.  Use the
same command for every later build::

    env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME LC_ALL=C.UTF-8 CCACHE_DIR=PREFIX/ccache make stage

``CCACHE_DIR`` keeps the compiler cache under the prefix, not under
``HOME``.  With ``configure --with-ccache`` the compiler of the
installation runs ccache too, so every test and every program that
compiles a module for the C++ backend reads the variable.  For a shell
outside the clean environment, say once
``ccache --set-config cache_dir=PREFIX/ccache``.
``SPRITE_SETUP_CLEAN_PATH`` replaces the PATH of the clean environment.

Layout of the prefix
====================

================================  ==============================================
Path                              Content
================================  ==============================================
``PREFIX/downloads``              the PAKCS archive
``PREFIX/pakcs-3.4.1``            PAKCS: ``bin/pakcs``, ``bin/pakcs-frontend``,
                                  ``bin/cypm``
``PREFIX/conda/env``              the conda environment; ``bin/python`` is the
                                  Python of Sprite
``PREFIX/conda/pkgs``             the conda package cache
``PREFIX/install``                the staged install, linked from the checkout
``PREFIX/object-root``            the object tree, linked from the checkout
``PREFIX/cpm``                    the CPM home, with ``--icurry``
``PREFIX/ccache``                 the compiler cache (``CCACHE_DIR`` of the
                                  clean environment)
``PREFIX/configure-args``         the flags of the last configure run
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
``--jobs N|auto``    the job count for configure, when it supports
                     ``--jobs``; auto is one job per processor, counted
                     by ``make`` when it starts
``--reconfigure``    run configure although ``Make.config`` exists and the
                     flags are the ones of the last run; ``make stage``
                     then rebuilds everything
``--dry-run``        print every command, run none
``--skip-apt``       do not check the apt packages
``--icurry``         also install icurry 3.1.0 through cypm
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

Every budget is a parameter: the job count, the memory cap, and the time
limit.  The script detects the cores and the memory and prints them.  Do
not copy a number from one machine to the next.

After the setup
===============

The last step prints the same list with the paths of the machine.

1. Calibrate the test manifest on the new machine.  Run every test file
   once per backend on a quiet machine with the manifest update of the
   test runner::

       cd tests
       ./run_tests -j 1 --backend both --update-manifest

   The durations and the peak memory of every test file must be measured
   there, then committed in ``tests/manifest.json``.  See ``./run_tests -h``
   and section 10 of ``tests/README``.
2. Record a baseline with the benchmark harness on a quiet machine.  The
   records carry the deterministic columns steps, forks, and collections,
   which the compare command checks::

       cd tests
       ./run_benchmarks -b cxx -b py --label baseline -o PREFIX/baseline.jsonl
       ./run_benchmarks counters PREFIX/baseline.jsonl

3. Update the personal rules file with the new paths: the Python, the
   PAKCS tree, icurry, the install and object trees, the conda package
   cache, the compiler cache, and the clean environment.  Record the cores
   and the memory.
4. Copy ``tests/.cache/icurry.db`` from the old machine.  The cache is
   keyed by the source text, so the first suite run then compiles nothing.

Notes
=====

- PAKCS, cypm, and icurry write under ``/tmp``.  A sandbox that mounts
  ``/tmp`` read-only breaks them.
- The Kiel mirrors of the Curry Package Manager do not answer.  The script
  writes a ``~/.cpmrc`` that names ``cpm.curry-lang.org``.
- The script was written for Ubuntu 24.04.  On another distribution,
  install the equivalents of the apt packages and pass ``--skip-apt``.
- ``tests/unit_setup_script.py`` runs the script with ``--dry-run`` and
  checks the plan.  It needs no network and installs nothing.
