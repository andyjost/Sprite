.. _easy-install:

Installation
============

On Linux or macOS, choose the path that fits your Python setup. On Windows,
take the pip path with a Python of your own: the one-line installer is for
Linux and macOS.

Without a suitable Python
-------------------------

The installer brings its own Python and leaves the Python of the operating
system alone. Run::

    curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh

For confirmation before each installation step, use::

    curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite-i | sh

The scripts install uv if needed, then use it to download a managed CPython
3.11.4 or newer (through 3.15) and install ``curry`` with its dependency
``curry-frontend`` in an isolated environment in your home directory. They
never use sudo. Run the script again to
upgrade Sprite.

Add the commands ``sprite-exec`` and ``sprite-make`` to your PATH for this
shell and put the same line in your shell startup file::

    export PATH="$HOME/.local/bin:$PATH"

To preview the plan without installing anything, download either script
and run ``sh getsprite --dry-run`` or ``sh getsprite-i --dry-run``.

With your own Python
--------------------

If you already have Python 3.11.4 or newer (through 3.15), install into your
Python environment with::

    pip install --pre curry

The ``--pre`` flag is needed while Sprite is in alpha. This installs
``curry-frontend`` too. If you want better performance and your platform
supports llvmlite, add the ``jit`` extra: ``pip install --pre
"curry[jit]"``. The wheels work with plain pip;
uv is a dependency of the installer alone. See :doc:`SoftwareCompatibility` for platform support and
:doc:`ManualInstallation` for installation from source.

Check the installation
----------------------

The Python that holds the package runs Curry too. Run a Curry program, or
open the Curry REPL with no argument::

    python -m curry Peano.curry
    python -m curry

A C++ compiler is optional. Without one, new modules run interpreted;
see :doc:`WithoutCompiler`.

Build a checkout as :doc:`ConfiguringSprite` describes.

Editor support
--------------

Vim highlights ``.curry`` files as Haskell when
``~/.vim/ftdetect/curry.vim`` holds one line:

.. code-block:: vim

    au BufRead,BufNewFile *.curry set filetype=haskell

.. toctree::

   ManualInstallation
   ConfiguringSprite
   WithoutCompiler

See :ref:`curry-packages` to use packages from the Curry Package Manager.
