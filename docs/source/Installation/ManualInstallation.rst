.. highlight:: bash
.. _custom-install:

===================
Manual Installation
===================

PyPI wheels and source distribution
-----------------------------------

The ``currylang`` package provides Sprite and is imported as ``curry``.
The initial release is ``0.9.0a1`` (alpha). Install it with::

  python -m pip install --pre currylang

The manylinux_2_28 wheels support Linux with glibc 2.28 or newer on x86-64
and aarch64, for CPython 3.11, 3.12, 3.13, 3.14, free-threaded 3.14t,
and 3.15. They include the compiled Curry library. A C++ compiler is
optional at run time: without one, Sprite interprets new modules; with
``g++`` installed, ``sprite-make --so Peano.curry`` compiles a module
using the user's compiler. Run a source program with
``python -m curry Peano.curry``.

The sdist builds with pip, a C++ compiler and the Python development
headers::

  python -m pip install --pre --no-binary=currylang currylang

Pip supplies CMake, Ninja and ``curry-frontend`` as build requirements.
It is also a runtime dependency, installed automatically to load source
programs after the build. PAKCS, SWI-Prolog, Haskell and GNU make are
unnecessary for this route. Before ``curry-frontend`` is published, download
its wheel from a successful ``frontend.yml`` run on master and pass its directory with
``--find-links`` to the pip command.

Building a checkout
-------------------

The Curry front end can be supplied by the ``curry-frontend`` platform
wheel. ``-DWITH_CURRY_FRONTEND=curry-frontend`` selects its console
script on PATH; ``SPRITE_FRONTEND`` selects it during configuration
and at run time. See :doc:`ConfiguringSprite` for the lookup order and the
standalone installation without PAKCS.

.. toctree::
  ConfiguringSprite
  BuildingSprite

