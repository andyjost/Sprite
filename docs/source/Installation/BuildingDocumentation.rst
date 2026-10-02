.. highlight:: bash

Building Documentation
======================

The documentation is not hosted online.  Build it locally.  From the
repository root, say ``make -C docs html``.  The HTML output is written under
``object-root/docs/html``.  The sources live under ``docs/`` in the `GitHub
repository <https://github.com/andyjost/Sprite>`__.  You can also choose a
different format, as described below.

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


