================
Troubleshooting
================

Compatibility
=============

Sprite was developed and tested with the following software:

- Ubuntu Linux 16.04.6 LTS
- Python 2.7.18, 3.5.2, 3.9.4
- PAKCS 3.4.1
- ICurry Compiler 3.1.0 (Version of 28/07/21)
- SWI Prolog 8.0
- Curry Package Manger 3.1.0
- gcc 7.4.0
- GNU Make 4.1
- pybind11 ``acae930123bcd331aff73a30e4fb7e2103fd7fca``

Known compatibility problems are discussed below.

PAKCS
    The Curry Prelude is obtained from PAKCS.  Sprite relies on the internal
    interface of the Prelude, which is unstable.  Because of this, Sprite will
    almost certainly not work with any other version of PAKCS.

ICurry
    The output of ICurry is historically unstable.  Sprite will not work with
    older (and possibly newer) versions of ICurry.


Python
    Although Python 2 has reached its end-of-life, it is still actively used.
    Sprite works with the final version of Python 2, namely 2.7.18.  Older
    versions (in particular 2.7.12) fail to build due to incompatibilities with
    pybind11.
    
    Sprite is expected to work with all Python versions from 3.5.2 forward.

Sources
=======

- Python is available through most software package managers.  For fine control
  over the version on Ubuntu, consider using the `deadsnakes PPA
  <https://github.com/deadsnakes>`_.  To build from source, download Python
  `here <https://www.python.org/downloads/>`__.

- Prolog is available `here <https://www.swi-prolog.org>`__.  It is a
  prerequisite of PAKCS.

- Download PAKCS `here <https://www.informatik.uni-kiel.de/~pakcs/download.html>`__.

- ICurry is available through the `Curry Package Manager`_.  After installing
  PAKCS, say the following from your home directory:

  .. code:: bash

      cypm update
      cypm add icurry

- `pybind11 <https://github.com/pybind/pybind11>`_ is automatically cloned into
  Sprite via the ``git submodules`` command the first time ``make`` is run.
  

.. _Curry Package Manager: https://www-ps.informatik.uni-kiel.de/currywiki/tools/cpm
