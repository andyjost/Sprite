.. highlight:: bash

Building Documentation
======================

The user guide of the ``master`` branch is published at
https://andyjost.github.io/Sprite/.  To read the guide of the branch you
have, build it locally.  From the repository root, say ``make -C docs
html``.  The HTML output is written under ``object-root/docs/html``.  The
sources live under ``docs/`` in the `GitHub repository
<https://github.com/andyjost/Sprite>`__.  You can also choose a different
format, as described below.  The build regenerates the Reference pages
from the staged installation and the usage pages from the installed tools,
so it needs ``make stage`` first.  Sphinx does not delete the output of a
source page that vanished, and ``make -C docs html`` has no clean step.
After a change to the set of Reference pages, say ``make -C docs clean``
before ``make -C docs html``.

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


