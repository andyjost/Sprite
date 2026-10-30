.. highlight:: bash
.. _custom-install:

===================
Manual Installation
===================

PyPI wheels and source distribution
-----------------------------------

The ``curry`` package provides Sprite and is imported as ``curry``.
The current release is ``0.9.0a2`` (alpha). Install it with::

  python -m pip install --pre curry

The manylinux_2_28 wheels support Linux with glibc 2.28 or newer on x86-64
and aarch64, for CPython 3.11, 3.12, 3.13, 3.14, free-threaded 3.14t,
and 3.15. The macOS wheels support macOS 15 or newer on Apple Silicon and
Intel, for the same interpreters (the wheel of the front end sets that
floor: its GMP is the Homebrew bottle of macOS 15). They include the
compiled Curry library. A C++ compiler is
optional at run time: without one, Sprite interprets new modules; with
``g++`` installed, ``sprite-make --so Peano.curry`` compiles a module
using the user's compiler. Run a source program with
``python -m curry Peano.curry``.

The sdist builds with pip, a C++ compiler and the Python development
headers::

  python -m pip install --pre --no-binary=curry curry

Pip supplies CMake and Ninja as build requirements; the build uses the
pinned products of the Curry library and needs no front end. The front
end ``curry-frontend`` 3.1.0, the version of those products, is a runtime
dependency, installed automatically to load source programs after the
build. PAKCS, SWI-Prolog, Haskell and GNU make are unnecessary for this
route.

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

