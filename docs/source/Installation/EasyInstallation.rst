.. highlight:: bash

.. _easy-install:

Easy Installation
=================

On Linux, choose the path that fits your Python setup.

Without a suitable Python
-------------------------

The installer brings its own Python; you do not need to replace the Python
of your operating system. Run::

    curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh

For confirmation before each installation step, use::

    curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite-i | sh

The scripts install uv if needed, then use it to download a managed CPython
3.11.4 or newer (through 3.15) and install ``curry`` with its dependency
``curry-frontend`` in an isolated environment in your home directory. They
leave the system Python alone and never use sudo. Run the script again to
upgrade Sprite.

Add the commands ``sprite-exec`` and ``sprite-make`` to your PATH for this
shell, and put the same line in your shell startup file::

    export PATH="$HOME/.local/bin:$PATH"

To preview the plan without installing anything, download either script
and run ``sh getsprite --dry-run`` or ``sh getsprite-i --dry-run``.

With your own Python
--------------------

If you already have Python 3.11.4 or newer (through 3.15), install into your
Python environment with::

    pip install --pre curry

The ``--pre`` flag is needed while Sprite is in alpha. This installs
``curry-frontend`` too. The wheels work with plain pip;
uv is a dependency of the installer alone. See :ref:`custom-install` for
platform support and installation from source.

From Python
-----------

Python developers can use the Python they installed into as the front door.
Run a Curry source program, or open the Curry REPL with no argument::

    python -m curry MyProgram.curry
    python -m curry

A C++ compiler (``g++``) is optional. Without one, new modules run interpreted;
see :doc:`WithoutCompiler`.
