.. _without-compiler:

Installing and Running Without a C++ Compiler
=============================================

Sprite runs every Curry program without a C++ compiler. The C++ runtime
interprets a module without a current object; ``pip install --pre
"curry[jit]"`` adds LLVM compilation of hot functions in process. LLVM
needs the installation's ``lib/curryrt-helpers.bc``, built with clang;
every wheel carries it. :doc:`/CompilationOptions` describes the modes
and flags. With neither llvmlite nor a compiler, the interpreter runs
alone and notes it once per process in its log.

A source build records its compiler at ``tools/cxx``. A wheel uses
``CXX`` or ``g++`` on PATH, and on Windows clang-cl or cl of Visual Studio
in a developer prompt (``vcvars64.bat``). The runtime library, its bindings
and the Curry front end need no compiler at run time.

The cost
--------

Interpreted evaluation takes about 1.5 times the time of compiled code
(``Tak1``: 1.9 s against 1.3 s). Module images avoid parsing and optimizing
ICurry at each start: an interpreted Prelude import took 0.039 s in
process after warm-up and a trivial ``sprite-exec`` process took 0.142 s
with images. These measurements exclude translation of missing or stale
images. The stage and wheels ship library images alongside their objects;
keep them and the default ``interpret:new``.

Adding a compiler later
-----------------------

Install ``g++``, clang++ from Xcode or clang-cl from Visual Studio. With a
pip installation, the next process finds ``CXX`` or ``g++`` on PATH. A
checkout gets its ``tools/cxx`` from ``make stage``;
``-DWITH_CXX_POSTINSTALL=PATH`` names the compiler
(:doc:`ConfiguringSprite`).
