======================
Software Compatibility
======================

Sprite was developed and tested with the following software:

- Ubuntu Linux 24.04 LTS
- Python 3.14
- PAKCS 3.4.1, with the Curry front end 2.0.0 that it ships
- SWI-Prolog 9.0.4
- g++ 13.3
- GNU Make 4.3
- pybind11 v3.1.0

Known compatibility problems are discussed below.

PAKCS
    Sprite ships a copy of the Curry library of PAKCS 3.4.1 under
    ``curry/lib`` and relies on the internal interface of that Prelude, which
    is unstable.  PAKCS itself provides the Curry front end, which translates
    Curry to FlatCurry, and the test oracle.  Sprite will almost certainly not
    work with any other version of PAKCS.

ICurry
    Sprite translates FlatCurry to ICurry itself.  Its translation is a port
    of the ICurry Compiler 3.1.0 and writes the same files.  That program,
    installed with the Curry Package Manager, remains an optional
    alternative; see ``configure --with-icurry``.  The output of other
    versions of the ICurry Compiler differs, and Sprite will not work with
    them.

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
  
  - The ICurry Compiler (optional) is available through the `Curry Package
    Manager`_.  After installing PAKCS, say the following from your home
    directory:
  
    .. code:: bash
  
        cypm update
        cypm add icurry
  
  - `pybind11 <https://github.com/pybind/pybind11>`_ is automatically cloned into
    Sprite via the ``git submodules`` command the first time ``make`` is run.
  

  .. _Curry Package Manager: https://www.curry-lang.org/tools/cpm/
