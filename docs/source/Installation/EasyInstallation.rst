.. highlight:: bash

.. _easy-install:

Easy Installation
=================

If you don't mind letting Sprite install missing dependencies, all you need to
do is issue `one` of the commands below.

  - **Automated** (no confirmation)::

        wget -qO- https://raw.githubusercontent.com/andyjost/Sprite/release/getsprite | sh

    or::

        curl -sSL https://raw.githubusercontent.com/andyjost/Sprite/release/getsprite | sh

  - **Interactive** (confirmation at each step)::

        wget -qO- https://raw.githubusercontent.com/andyjost/Sprite/release/getsprite-i | sh

    or::

        curl -sSL https://raw.githubusercontent.com/andyjost/Sprite/release/getsprite-i | sh

These commands may ask for root access to install dependencies using your
platform's package manager (currently, only apt is supported) and Python's
package manger (pip).

Sprite is installed under $HOME/Sprite.  If you prefer another location, you
can afterwards say::

    make -C $HOME/Sprite install PREFIX=/path/to/sprite


