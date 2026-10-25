======================
Software Compatibility
======================

Sprite was developed and tested with the following software:

- Ubuntu Linux 24.04 LTS
- Python 3.14
- PAKCS 3.10.0, with the Curry front end 3.1.0 that it ships
- SWI-Prolog 9.0.4, which runs PAKCS (the test oracle); Sprite itself runs
  no Prolog
- g++ 13.3
- GNU Make 4.3
- pybind11 v3.1.0

macOS on Apple Silicon builds the runtime and runs the C++ backend as
Linux does, the compiled modules and the background compile of the tiered
mode included (issues #162 and #163), with the front end built from source
by the CI job of the repository; a front end package for macOS is the next
step of issue #162.

Known compatibility problems are discussed below.

PAKCS
    Sprite ships a copy of the Curry library of PAKCS 3.10.0 (base 3.4.0) under
    ``curry/lib`` and relies on the internal interface of that Prelude, which
    is unstable.  PAKCS itself provides the Curry front end, which translates
    Curry to FlatCurry, and the test oracle.  The default configuration is front end 3.1.0 with PAKCS
    3.10.0. Front end 2.0.0 with PAKCS 3.4.1 remains supported, with advisory
    ``legacy-tools`` Linux unit and functional shards. Front-end packages
    are 2.0.0.post6 and 3.1.0.post1, with separate parity references.

ICurry
    Sprite translates FlatCurry to ICurry itself.  Its translation is a port
    of the ICurry Compiler 3.3.0 (3.1.0 for the legacy pair) and writes
    the same files in compatibility mode.  That program,
    installed with the Curry Package Manager, remains an optional
    alternative; see ``CMake WITH_ICURRY``.  CMake checks the compiler version against the selected front end.

Python
    Sprite supports Python 3.11 to 3.15, with 3.11.4 as the minimum because
    archive extraction uses ``tarfile.extractall(filter=)``.  CMake
    rejects older versions.  Python 3.14 remains the development default.
    CI runs the C++ unit suites on each version.  The 3.15 lane and the
    free-threaded 3.14t lane are allowed to fail; 3.14t runs with the GIL
    enabled (``PYTHON_GIL=1``), until the extension declares its thread
    safety.  Children inherit ``PYTHON_GIL`` when set.  Running Sprite
    without the GIL is not yet supported.

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
