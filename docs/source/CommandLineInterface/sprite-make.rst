.. _sprite-make:

===============
``sprite-make``
===============

``sprite-make`` runs the :ref:`compilation pipeline <compilation-pipeline>`
on a module up to the requested product: ICurry (``--icy``), a module
image (``--image``), C++ (``--cxx``) or an object (``--so``).
``make stage`` uses it to compile the Curry library into the installation.
It also writes intermediate forms for inspection.

``sprite-make -h`` prints the usage and ``sprite-make --man`` the manual;
both follow.

``sprite-make`` Manual
======================

.. include:: sprite-make-usage.rst

.. include:: sprite-make-man.rst

Generating ICurry
=================

``--icy`` writes the ICurry of a module. From ``examples/``::

    sprite-make --icy Peano.curry

The file goes to the subdirectory of intermediate products beside the
source; print its name with::

    sprite-make --subdir

``-o`` names another output file::

    sprite-make --icy Peano.curry -o Peano.icy

Generating module images
========================

To generate a runtime module image, supply ``--image``::

    sprite-make --image Peano.curry -o Peano.img

This is also the default target. It implies ``--icy``; ``--cxx`` and
``--so`` imply ``--image``. The translation record stays beside the image
for inspection and saving, including with ``--tidy``.

Compiling ahead of time
=======================

``--so`` compiles a module ahead of time into a shared object that the
runtime loads. It implies ``--cxx`` and needs a C++ compiler. A staged
installation uses ``tools/cxx``; a wheel uses ``CXX`` or ``g++`` on PATH::

    sprite-make --so Peano.curry

The object is written to ``.curry/sprite-pakcs-<ver>/Peano.so`` beside its
ABI stamp and loads whenever the module is imported. It is compiled again
when the runtime, the compiler or an imported module changed. The product
cache keeps a copy (``SPRITE_PRODUCT_CACHE``, :doc:`/DevelopmentVariables`).
