.. highlight:: bash

Configuring Sprite
==================

The build system must first be configured by running ``configure``.  That
script finds, verifies, and (optionally) installs prerequisites.

``configure`` Manual
--------------------

.. include:: configure-usage.rst

Configuration Options
---------------------

Sprite relies on several external programs.  ``configure`` searches PATH for
these, using a default name for each program.

To adjust this behavior, supply one or more ``--with-*`` options or,
equivalently, set the corresponding environment variable(s).  An absolute path
may be supplied, or the name to search for can be changed.

These options are summarized in the following table:

+-------------------+-------------+-------------+---------------------------+
| Option            | Environment | Default     | Description               |
|                   | Variable    |             |                           |
+===================+=============+=============+===========================+
| ``--with-cc``     | CC          | ``gcc``     | Selects the C compiler    |
+-------------------+-------------+-------------+---------------------------+
| ``--with-cxx``    | CXX         | ``g++``     | Selects the C++ compiler  |
+-------------------+-------------+-------------+---------------------------+
| ``--with-icurry`` | ICURRY      | ``icurry``  | Selects ICurry            |
+-------------------+-------------+-------------+---------------------------+
| ``--with-pakcs``  | PAKCS       | ``pakcs``   | Selects PAKCS             |
+-------------------+-------------+-------------+---------------------------+
| ``--with-prolog`` | PROLOG      | ``swipl``   | Selects Prolog            |
+-------------------+-------------+-------------+---------------------------+
| ``--with-python`` | PYTHON      | ``python``  | Selects Python            |
+-------------------+-------------+-------------+---------------------------+
| ``--with-stack``  | STACK       | ``stack``   | Selects Haskell Stack     |
+-------------------+-------------+-------------+---------------------------+

For example, suppose Python 3.14 is installed but it is not the system
default.  Say::

    ./configure --with-python=python3.14 [args...]

If you have a custom build of Python not in PATH, you might say::

    ./configure --with-python=/path/to/python [args...]

To use the Clang compilers (searching PATH for them), one might say::

    ./configure --with-cc=clang --with-cxx=clang++ [args...]

If CC and CXX were set in the environment, this would happen anyway.

Checking Prerequisites
----------------------

Once you have determined your configuration options, check the prerequisites::

    ./configure [your-config-options...] --check-prereqs

If ``configure`` reports problems, you may need to:

    1. Adjust PATH;
    2. Change configuation options; or
    3. Install missing software.

``configure`` can attempt to install missing software for you.  If you are
satisfied with the steps proposed by ``./configure --check-prereqs`` then say::

    ./configure [your-config-options...] --install-prereqs-only --yes

Omit ``--yes`` if you prefer to confirm each step.

To install these yourself, follow the instructions at the links below:

  * Python 3.14 with development files.
      - The `deadsnakes PPA <https://github.com/deadsnakes>`__ is a good
        source.  Be sure to install the -dev package: install ``python3.14``
        `AND` ``python3.14-dev``.
  * `PAKCS 3.4.1 <https://www.curry-lang.org/pakcs/>`__
      - Prerequisites for PAKCS are:
          - `Haskell stack <https://docs.haskellstack.org/en/stable/install_and_upgrade>`__
          - Prolog (`SWI <https://www.swi-prolog.org/download/stable>`__ or `SICStus <https://sicstus.sics.se/download4.html>`__)
  * `ICurry Compiler 3.1.0 <https://cpm.curry-lang.org/pkgs/icurry.html>`__

Setting the Configuration
-------------------------

Once the prerequisite check succeeds, run ``configure`` once more to set the
configuration::

    ./configure [your-config-options...]

This creates a file ``Make.config`` containing the configuration settings.
Inspect this file and make adjustments, if you like.

To install prerequisites and configure in one step, say::

    ./configure [your-config-options...] --install-prereqs [--yes]

