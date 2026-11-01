======================
Software Compatibility
======================

Sprite builds and runs its tests with this software:

- Ubuntu Linux 24.04 LTS
- Python 3.14
- PAKCS 3.10.0, with the Curry front end 3.1.0 that it ships
- SWI-Prolog 9.0.4, which runs PAKCS (the test oracle); Sprite itself runs
  no Prolog
- g++ 13.3
- GNU Make 4.3
- pybind11 3.1.0

The wheels support CPython 3.11, 3.12, 3.13, 3.14, free-threaded 3.14t
and 3.15 on these platforms:

* Linux x86-64 and Linux aarch64, with glibc 2.28 or newer.
* macOS arm64 and macOS x86-64, with macOS 15 or newer.
* Windows x64.

Linux and macOS wheels include the compiled Curry library. A C++ compiler
is optional at run time. Windows modules run interpreted or through the
LLVM JIT (``pip install --pre 'curry[jit]'``); no module is compiled with a
C++ compiler there. Both ``curry`` and ``curry-frontend`` have wheels for
these platforms.

Notes on each component follow.

PAKCS
    Sprite ships a copy of the Curry library of PAKCS 3.10.0 (base 3.4.0) under
    ``curry/lib`` and relies on the internal interface of that Prelude, which
    is unstable.  PAKCS itself provides the Curry front end, which translates
    Curry to FlatCurry and serves as the test oracle.  The default configuration is front end 3.1.0 with PAKCS
    3.10.0. Front end 2.0.0 with PAKCS 3.4.1 remains supported; CI tests that pair
    on Linux. The distribution ``curry`` depends on 3.1.0, the version of its pinned
    library products, which 2.0.0 cannot read.

ICurry
    Sprite translates FlatCurry to ICurry itself.  Its translation is a port
    of the ICurry Compiler 3.3.0 (3.1.0 for the legacy pair) and writes
    the same files in compatibility mode.  That program,
    installed with the Curry Package Manager, remains an optional
    alternative; see ``WITH_ICURRY`` on :doc:`ConfiguringSprite`.  CMake checks the compiler version against the selected front end.

Curry preprocessor
    ``currypp`` is optional and is shipped by neither Sprite nor the
    package of the front end. Modules whose OPTIONS_CYMAKE pragma names
    ``--pgmF=currypp`` need it on PATH when compiling from source.
    Install the preprocessor for your PAKCS installation with its Curry
    Package Manager, then put the package manager's executable directory
    on PATH:

    .. code-block:: bash

        cypm update
        cypm install currypp

    The tests skip source compilation when the tool is absent and use
    the products in the test archives. The benchmark harness
    records these programs as excluded, with the missing tool as the reason.

Python
    Sprite supports Python 3.11 to 3.15, with 3.11.4 as the minimum because
    archive extraction uses ``tarfile.extractall(filter=)``.  CMake
    rejects older versions.  Python 3.14 remains the development default.
    CI runs the unit suite on each version and on free-threaded 3.14t
    with ``PYTHON_GIL=0``. Children inherit ``PYTHON_GIL`` when set.

:doc:`/Status` lists how Sprite's library differs from PAKCS.
