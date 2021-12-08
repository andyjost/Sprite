.. highlight:: bash

Starting Python
===============

``sprite-invoke`` sets up the environment for Sprite.  It takes a command to be
run in the configured environment.  For example, to start a shell one could say::

    sprite-invoke $SHELL

For convenience, a wrapper script that starts Python under ``sprite-invoke`` is also
provided.  Given an installation tree located at PREFIX, this script is located
at ``$PREFIX/bin/python``.

Starting Python through this script has the added benefit of ensuring the correct
Python version is used.

.. warning::

    Sprite is only compatible with the Python speicified during configuration.
    Using a different version will result in undefined behavior.

After running ``make stage``, you can start using Sprite as follows::

    % ./install/bin/python
    >>> import curry
    >>>

.. tip::

    Use the wrapper script as an interpreter to simplify configuration.  If
    Sprite is installed under ``/path/to/sprite``, then begin scripts with::

        #!/path/to/sprite/bin/python

