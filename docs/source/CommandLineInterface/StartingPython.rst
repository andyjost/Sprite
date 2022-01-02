.. highlight:: bash

.. _starting-python:

Starting Python
===============

A Sprite-enabled Python session can be started by running the ``python``
wrapper script that appears under the Sprite installation tree.  After running
``make stage``, say::

    % ./install/bin/python
    >>> import curry
    >>>

.. tip::

    Use the wrapper script as an interpreter to simplify configuration.  If
    Sprite is installed under ``/path/to/sprite``, then begin scripts with::

        #!/path/to/sprite/bin/python

.. _sprite-invoke:

``sprite-invoke``
-----------------

``sprite-invoke`` sets up the environment for Sprite.  This ensures the Sprite
libraries can be located at runtime.  It takes a command to be run in the
configured environment.  Passing your shell as the command is an easy way to
inspect Sprite's environment::

    sprite-invoke $SHELL

The Python wrapper script mentioned above uses ``sprite-invoke`` to start
Python.  This method ensures the correct Python is used.  Sprite is only
compatible with the Python specified during configuration and using another
results in undefined behavior.

The original Python can be found under ``tools/`` in the installation
directory.

``sprite-invoke`` is useful when you want another program to start Python.  For
example, to run under gdb, you might say::

    sprite-invoke gdb install/tools/python

