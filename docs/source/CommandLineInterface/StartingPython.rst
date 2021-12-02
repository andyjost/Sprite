.. highlight:: bash

Starting Python
===============

Sprite requires the environment be configured for Python to find its libraries
and code.  ``sprite-invoke`` is supplied for this purpose.  It takes a command
and arguments to run in the configured environement.  To start a shell
configured for Sprite, say::

    sprite-invoke $SHELL

Sprite provides a wrapper script that starts Python under ``sprite-invoke``.
To use it, run the program found at ``$PREFIX/bin/python``, where
PREFIX is the root of Sprite's installation tree.

.. note::

    After staging Sprite with ``make stage`` an installation tree can be found
    at ``install/``.

Starting Python this way also ensures the version that Sprite was configured
and tested with is used.

.. warning::

    Sprite is only compatible with the Python speicified during configuration.
    Using a different version results in undefined behavior.
