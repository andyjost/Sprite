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

+---------------------------+----------------+--------------------+---------------------------------+
| Option                    | Environment    | Default            | Description                     |
|                           | Variable       |                    |                                 |
+===========================+================+====================+=================================+
| ``--with-cc``             | CC             | ``gcc``            | Selects the C compiler          |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-ccache``         | CCACHE         | none               | Puts ccache in front of the     |
|                           |                |                    | compilers (optional)            |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-cxx``            | CXX            | ``g++``            | Selects the C++ compiler        |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-curry-frontend`` | CURRY_FRONTEND | ``pakcs-frontend`` | Selects the Curry front end.    |
|                           |                | of PAKCS           | An empty value leaves it out.   |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-icurry``         | ICURRY         | none               | Selects icurry, the alternative |
|                           |                |                    | route to ICurry (optional)      |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-pakcs``          | PAKCS          | ``pakcs``          | Selects PAKCS.  An empty value  |
|                           |                |                    | leaves it out                   |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-prolog``         | PROLOG         | ``swipl``          | Selects Prolog                  |
+---------------------------+----------------+--------------------+---------------------------------+
| ``--with-python``         | PYTHON         | ``python``         | Selects Python                  |
+---------------------------+----------------+--------------------+---------------------------------+

Sprite translates Curry to ICurry in two steps: the Curry front end of PAKCS
writes FlatCurry, and Sprite's own code translates that to ICurry.  The
``icurry`` program of the Curry Package Manager does the same work and is
kept as an alternative.  ``configure`` records it only when you pass
``--with-icurry``.  The option ``--curry2icurry`` names the route Sprite uses
by default; the environment variable ``SPRITE_CURRY2ICURRY`` overrides that
choice at run time.

PAKCS itself is optional.  Sprite needs its front end, which
``--with-curry-frontend`` can name directly, and the functional tests use
``pakcs`` as the oracle.  ``--with-pakcs ''`` builds without PAKCS; the
intermediate directories under ``.curry`` then take their names from the
pinned release, ``pakcs-3.4.1``, so the committed ICurry files stay valid.
The conda recipe under ``conda/`` builds this way; see ``conda/README.md``.

For example, suppose Python 3.14 is installed but it is not the system
default.  Say::

    ./configure --with-python=python3.14 [args...]

If you have a custom build of Python not in PATH, you might say::

    ./configure --with-python=/path/to/python [args...]

To use the Clang compilers (searching PATH for them), one might say::

    ./configure --with-cc=clang --with-cxx=clang++ [args...]

If CC and CXX were set in the environment, this would happen anyway.

Build options
-------------

``configure --jobs N`` sets the number of jobs that ``make`` runs at once.
``--jobs auto`` gives one job per processor, counted when ``make`` starts.
The default is 1, a serial build.  ``configure`` writes the value to
``Make.config`` as ``JOBS``, so ``make stage`` runs in parallel without
``-j``.  A ``-j`` on the ``make`` command line wins, and so does
``make JOBS=N``.

``configure --with-ccache`` puts ccache in front of the compilers.  The
build compiles every object through ccache.  The compiler of the
installation, ``tools/cxx``, becomes a script that runs ccache in front of
the post-install compiler, so the code of the C++ backend compiles through
ccache as well.  The value names the program (``--with-ccache=PATH``); by
default ``configure`` searches PATH for ``ccache``.  ccache changes nothing
in the output of the compiler, and the ABI stamps of compiled modules do not
depend on it.  To share one cache between several copies of the source
tree, set ``base_dir`` in the ccache configuration to a common parent
directory.

The setting for development work is::

    ./configure --jobs auto --with-ccache [args...]

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
      - The binary distribution includes the Curry front end,
        ``bin/pakcs-frontend``.
  * Optional: `ICurry Compiler 3.1.0 <https://cpm.curry-lang.org/pkgs/icurry.html>`__,
    the alternative route from Curry to ICurry.

Setting the Configuration
-------------------------

Once the prerequisite check succeeds, run ``configure`` once more to set the
configuration::

    ./configure [your-config-options...]

This creates a file ``Make.config`` containing the configuration settings.
Inspect this file and make adjustments, if you like.

To install prerequisites and configure in one step, say::

    ./configure [your-config-options...] --install-prereqs [--yes]

