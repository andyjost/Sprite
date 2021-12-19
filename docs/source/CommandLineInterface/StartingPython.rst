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

``sprite-invoke`` sets up the environment for Sprite.  It takes a command to be
run in the configured environment.  To start a shell configured for Sprite
say::

    sprite-invoke $SHELL

The wrapper script mentioned above uses :ref:`sprite-invoke` to start Python.
This method ensures the correct Python is used.  Sprite is only compatible with
the Python specified during configuration and using another results in
undefined behavior.

