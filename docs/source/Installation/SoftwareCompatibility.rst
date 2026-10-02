======================
Software Compatibility
======================

Sprite was developed and tested with the following software:

- Ubuntu Linux 24.04 LTS
- Python 3.14
- PAKCS 3.4.1
- ICurry Compiler 3.1.0
- SWI-Prolog 9.0.4
- Curry Package Manager 3.1.0
- g++ 13.3
- GNU Make 4.3
- pybind11 v3.1.0

Known compatibility problems are discussed below.

PAKCS
    The Curry Prelude is obtained from PAKCS.  Sprite relies on the internal
    interface of the Prelude, which is unstable.  Because of this, Sprite will
    almost certainly not work with any other version of PAKCS.

ICurry
    The output of ICurry is historically unstable.  Sprite will not work with
    older (and possibly newer) versions of ICurry.

Python
    Sprite requires Python 3.14.  ``configure`` rejects older versions.

..
  Sources
  =======
  
  - Python is available through most software package managers.  For fine control
    over the version on Ubuntu, consider using the `deadsnakes PPA
    <https://github.com/deadsnakes>`_.  To build from source, download Python
    `here <https://www.python.org/downloads/>`__.
  
  - Prolog is available `here <https://www.swi-prolog.org>`__.  It is a
    prerequisite of PAKCS.
  
  - Download PAKCS `here <https://www.curry-lang.org/pakcs/>`__.
  
  - ICurry is available through the `Curry Package Manager`_.  After installing
    PAKCS, say the following from your home directory:
  
    .. code:: bash
  
        cypm update
        cypm add icurry
  
  - `pybind11 <https://github.com/pybind/pybind11>`_ is automatically cloned into
    Sprite via the ``git submodules`` command the first time ``make`` is run.
  

  .. _Curry Package Manager: https://www.curry-lang.org/tools/cpm/
