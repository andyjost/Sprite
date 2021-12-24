.. highlight:: bash

Building Documentation
======================

The HTML documentation is available `online
<http://web.cecs.pdx.edu/~josta/sprite>`__.  You can build a local copy of that
or choose a differen format.

.. important::
   Sprite is required to build the documentation.  If needed, build and stage
   it first.

To check prerequisites, say::

    ./configure --check-prereqs --doc --fast

If anything is missing, you can install it yourself or say::

    ./configure --with-python=`pwd`/install/tools/python --install-prereqs-only --doc --fast

To build PDF and HTML documentation, say::

    make docs

To build documentation in another format, say::

    make -C docs <format-name>

Many formats are available; say ``make -C docs help`` for details.


