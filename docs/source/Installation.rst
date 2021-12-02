.. highlight:: bash

============
Installation
============

.. important::

    Refer to the :ref:`External Software
    <Introduction/ExternalSoftware:External Software>` list to ensure
    compatible prerequisites are installed.

Short Instructions
==================

From the Sprite repository root, say::

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

The default target builds Sprite, installs it to a staging area, and runs the
tests::

    make

If you prefer to do things one step at a time, follow the instructions below.

You must initialize and update the GIT submodules before building Sprite::

    git submodule init
    git submodule update

To overlay pre-built ICurry files for the Curry standard library and tests,
say::

    make overlay

.. important::

    This step avoids converting hundreds of Curry files to ICurry, which
    accelerates the first invocation of these tests by **several hours**.  To
    use this, your version of PACKS must match one of the ``overlay*.tgz``
    files at the repository root.

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

You can also say ``cd tests && ./run_tests``.  See tests/README for information
about the test system.

To install Sprite to a directory, ``/path/to/sprite``, of your choosing say::

    make install PREFIX=/path/to/sprite

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

Syntax Highlighting for Spritelog Files
---------------------------------------

To install Vim syntax highlighting for files ending with ``spritelog`` do the
following:

  1. Copy ``spritelog.vim`` from the repository root to
     ``~/.vim/syntax/spritelog.vim``.
  2. Create the file ``~/.vim/ftdetect/spritelog.vim`` with the following
     contents:

     .. code-block:: vim

         au BufRead,BufNewFile *spritelog set filetype=spritelog

