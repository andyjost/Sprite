.. _custom-install:

Manual Installation
===================

Source distribution
-------------------

The source distribution builds with pip, a C++ compiler and the Python
development headers::

    pip install --pre --no-binary=curry curry

CMake and Ninja come from pip as build requirements. The build checks the
shipped Curry library sources against their pinned ICurry and interfaces,
then builds from those products without a Curry front end. The runtime
dependency ``curry-frontend`` is installed automatically to compile new
Curry text. PAKCS, SWI-Prolog, Haskell and GNU make are unnecessary for
this route. On Windows the compiler is clang-cl of Visual Studio in a
developer prompt (``vcvars64.bat``); cl is experimental.
:doc:`SoftwareCompatibility` lists the supported platforms.

Building a checkout
-------------------

To build from a checkout, follow :doc:`ConfiguringSprite`.

See :ref:`curry-packages` to use packages from the Curry Package Manager.
