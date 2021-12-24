.. highlight:: bash

==================
Installation Guide
==================

Configuring the Build
=====================

Find Missing Prerequisites
..........................

Sprite requires the following software:

  * `Python <https://github.com/deadsnakes>`__ 2.7.18, or 3.5.2+, with development files.
    (Example: install python3.9 `AND` python3.9-dev.)
  * `PAKCS 3.4.1 <https://www.informatik.uni-kiel.de/~pakcs/download.html>`__
    * `Haskell stack <https://docs.haskellstack.org/en/stable/install_and_upgrade>`__
    * Prolog (`SWI <https://www.swi-prolog.org/download/stable>`__ or `SICStus <https://sicstus.sics.se/download4.html>`__)
  * `ICurry Compiler 3.1.0 <https://www-ps.informatik.uni-kiel.de/~cpm/pkgs/icurry-3.1.0.html>`__
  * `jq <https://stedolan.github.io/jq/download>`__

If you already have some of these installed, ensure they are in your PATH (or
see the next section).  To check for missing prerequisites, say::

    ./configure --check-prereqs

If missing programs are detected, ``configure`` prints the commands it would
use to install them.

Selecting Programs
..................

For more control over the software used, ``configure`` provides ``--with-*``
options and environment variables.  These are summarized in the following
table:

+-------------------+----------------------+---------------------------+
| Option            | Environment Variable | Description               |
+===================+======================+===========================+
| ``--with-python`` | PYTHON               | Selects Python            |
+-------------------+----------------------+---------------------------+
| ``--with-pakcs``  | PAKCS                | Selects PAKCS             |
+-------------------+----------------------+---------------------------+
| ``--with-icurry`` | ICURRY               | Selects ``icurry``        |
+-------------------+----------------------+---------------------------+
| ``--with-cc``     | CC                   | Selects the C compiler    |
+-------------------+----------------------+---------------------------+
| ``--with-cxx``    | CXX                  | Selects the C++ compiler  |
+-------------------+----------------------+---------------------------+
| ``--with-prolog`` | PROLOG               | Selects Prolog            |
+-------------------+----------------------+---------------------------+
| ``--with-jq``     | JQ                   | Selects ``jq``            |
+-------------------+----------------------+---------------------------+
| ``--with-stack``  | STACK                | Selects Haskell ``stack`` |
+-------------------+----------------------+---------------------------+

For example, suppose you installed Python 3.11 from the `deadsnakes PPA
<https://github.com/deadsnakes>`__.  To use it, say::

    ./configure --with-python=python3.11 --check-prereqs

Alternatively, to specify Python via the environment, users of a BASH-like
shell might say::

    PYTHON=python3.11 ./configure --check-prereqs

Install Missing Prerequisites
.............................

If ``configure`` identifies missing programs, you must install them before
proceeding.  If you are satisfied with the steps proposed by ``./configure
--check-prereqs`` then say::

    ./configure --install-prereqs --yes

Otherwise, follow the links at the top of this page, then download and install
the missing software yourself.


Building Sprite (Short Instructions)
====================================

Follow these instructions to get started quickly.  If you prefer doing things
one step at a time, follow the instructions in the next section.

Run the following from the Sprite repository root::

    ./configure
    make

Running ``make`` with no arguments builds Sprite, installs it under
``install/``, and then runs the tests.


Building Sprite (Long Instructions)
===================================

Step 1: Configure the build
---------------------------

Begin by configuring Sprite::

    ./configure

Say ``./configure -h`` for help.  You can specify which Python, compilers,
PAKCS, and other tools to use.  With no arguments, the PATH is searched.
Supply ``-i`` to make selections interactively.  If ``configure`` complains,
follow the instructions to install missing software.

Following configuration, you can invoke ``make``.  Say ``make help`` for
information about targets and options.

Step 2: Initialize submodules
------------------------------

You must initialize and update the GIT submodules before building::

    git submodule init
    git submodule update

Step 3: Overlay ICurry files
----------------------------

To overlay pre-built ICurry files for the Curry standard library and tests,
say::

    make overlay


This step **saves several hours** by avoiding hundreds of Curry-to-ICurry
conversions.  See :ref:`important-notes`.

To use this, your version of PACKS must match one of the ``overlay*.tgz``
files at the repository root.

Step 4: Build objects and libraries
-----------------------------------

To build object files, static libraries, and shared libraries say::

    make objs libs shlibs

Step 5: Stage
-------------

To stage Sprite say::

    make stage

This must be done before tests are run.  It creates a mock installation under
``install/``.  This step also builds the necessary objects and libraries, so
you can skip the previous two steps if you like.

Step 6: Test
------------

To run the tests, say::

    make test

You can also say ``cd tests && ./run_tests``.  See tests/README for fine
control of testing.

Step 7: Install (optional)
--------------------------

You can use Sprite directly from the staging area.  If you prefer to install it
elsewhere, use ``make install`` while setting PREFIX to the desired location.

To install Sprite under ``/path/to/sprite`` say::

    make install PREFIX=/path/to/sprite

Refer to the :ref:`install tree layout <install-tree-layout>` for the
directories this creates.


Building Documentation
======================

.. note::

    Most people will not need to build the documentation.  It is available
    `here <http://web.cecs.pdx.edu/~josta/sprite/>`__.

To build PDF and HTML documentation, say::

    make docs

Many formats are available; say ``make -C docs help`` for details.

Installing Syntax Files
=======================

Syntax Highlighting for Curry Files
-----------------------------------

To associate the ``.curry`` extension with Haskell syntax in Vim create the
file ``~/.vim/ftdetect/curry.vim`` with the following contents:

.. code-block:: vim

    au BufRead,BufNewFile *.curry set filetype=haskell

.. _spritelog-highlighting:

Syntax Highlighting for Spritelog Files
---------------------------------------

If you plan to view computation traces generated by Sprite, consider installing
the syntax highlighting for ``spritelog`` files.  Do the following for Vim:

  1. Copy ``spritelog.vim`` from the repository root to
     ``~/.vim/syntax/spritelog.vim``.
  2. Create the file ``~/.vim/ftdetect/spritelog.vim`` with the following
     contents:

     .. code-block:: vim

         au BufRead,BufNewFile *spritelog set filetype=spritelog


.. toctree::
    Troubleshooting
