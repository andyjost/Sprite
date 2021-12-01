.. highlight:: bash

============
Installation
============

.. note::

   All commands must be run from the repository root.

Short Instructions
==================

.. code::

    ./configure
    make
    make install PREFIX=<install-dir>

Long Instructions
=================

Begin by configuring Sprite::

    ./configure

Say ``./configure -h`` for help.  You can specify which Python, compilers,
PAKCS, and other tools to use.  With no arguments, these tools are pulled from
the user's PATH.  Supply ``-i`` to make selections interactively.

The configuration script validates the selections.  If it complains, follow the
instructions to install missing software and retry configuration.

After successful configuration, you can invoke ``make``.  Say ``make help`` for
details about targets and other options.

The default target does everything needed to build Sprite, install it to a
staging area, and run the tests.  If you prefer to do things one step at a
time, follow the instructions below.

You must initialize and update the GIT submodules before building Sprite::

    git submodule init
    git submodule update

To overlay pre-built ICurry files for the Curry standard library and tests,
say::

    make overlay

This avoids having to compile many Curry files, which accelerates the first
invocation of the tests considerably.  Without this step, the first invocation
requires several hours to complete.  To use this, your version of PACKS must
match one of the ``overlay*.tgz`` files at the repository root.

To build object files say::

    make objs

To build static and shared libraries say::

    make libs shlibs

To stage the programs and libraries, say::

    make stage

This must be done before tests are run.  It creates a mock installation under
``install/``.  This step also builds the necessary objects and libraries, so
you can skip the previous two steps if you like.

To run the tests, say::

    make test

You can also say ``cd tests && ./run_tests``.  See tests/README for complete
documentation of the test system.

To install Sprite to a directory of your choosing say::

    make install PREFIX=<install-dir>

Sprite will be installed to the directory you specify.

To build PDF and HTML documentation, say::

    make docs

Many formats are available; say ``make -C docs help`` for details.
