.. _without-compiler:

=============================================
Installing and running without a C++ compiler
=============================================

The C++ backend, the default of Sprite, needs a C++ compiler for one thing:
to compile a Curry module to a shared object.  The runtime library
``libcurryrt``, its Python bindings, and the Curry front end need no compiler
at run time.  A module without a compiled object runs interpreted: the
runtime interprets the ICurry of the module from a bytecode, on the same
scheduler and with the same rewrite steps as compiled code (the interpreter
flag ``interpret``; see :doc:`/CompilationOptions`).  So an
installation without a C++ compiler runs every Curry program.

The build itself needs the compiler: CMake finds a C++ compiler, and
``make stage`` compiles the runtime library and the Curry library.  An
installation without a compiler is one that moved to another machine, or a
package such as the conda package of ``conda/README.md`` installed without
``cxx-compiler``.  Sprite looks for its compiler at ``tools/cxx`` under
``SPRITE_HOME``; when that file is missing, the installation has none.

The Curry front end is a separate runtime tool. The source distribution
ships the current pair's ICurry, interfaces, import records and source
receipts for every library module. Building it needs Python and a C++
compiler, without a Curry front end or PAKCS. CMake checks the receipts
before using the pins. Library modules and programs with existing products
run without the front end; new Curry text reports::

    no Curry front end found; set SPRITE_FRONTEND or put pakcs-frontend on PATH

Install ``curry-frontend`` to compile new Curry text. The legacy tool pair
still needs its front end to build the library.

What runs interpreted
=====================

``make stage`` and ``make install`` compile the Curry library into the
installation with the compiler of the build.  The ABI stamp beside each
object digests the runtime headers the generated code includes, the
flavor, the compiler of the build (as the build recorded it in
``sysconfig/cxx_compiler``, so an installation
without a compiler computes the same digest) and the format of the
generated code, and names the real path of
the installation as text, which a package manager rewrites at install time,
so the library loads compiled where it was built or where its package
installed it, and counts as stale when the installation is copied by hand to
another path. Changed imported interfaces or ICurry also invalidate an
object's ABI stamp, so it follows the same interpretation and rebuild rule.
The default ``interpret:new`` loads current objects and starts other
modules interpreted. ``interpret:all`` starts every module interpreted and
never opens an ahead-of-time object. ``interpret:off`` requires a C++
compiler for every missing object and fails with an error if it is absent.

The default ``jit:hot,jit_backend:auto`` selects LLVM when llvmlite
imports, so installing ``curry[jit]`` provides compiled execution without
a C++ compiler. The installation must include ``lib/curryrt-helpers.bc``
(the build makes it with clang). Hot functions compile in process and
swap at a scheduler safepoint; ``jit:eager`` compiles at module load.

Without llvmlite, auto selects the installation's C++ compiler and compiles
whole modules in a child process after the first hot function. With
neither backend, the interpreter runs alone and the ``curry`` logger emits
one WARNING notice per process: ``jit: no backend, interpreter only``
with the missing prerequisites. ``jit:off`` keeps interpreted functions
interpreted. Forced ``jit_backend:llvm`` or ``jit_backend:cxx`` fails at
reset or first import if unavailable; the error names ``pip install
curry[jit]`` or a C++ compiler. The C++ compiler backend is unavailable on
Windows.

The flags are set in ``SPRITE_INTERPRETER_FLAGS``; see
:doc:`/CommandLineInterface/EnvironmentVariables`.

The cost
========

The interpreter takes about 1.5 times the time of compiled code for the
evaluation of a program (``Tak1``: 1.9 s against 1.3 s on 2026-10-30; the
measurements of issues #31 and #64 gave 1.1 to 1.5).  A process that interprets the Prelude, under
``interpret:all`` or when the library objects are missing, first reads the
ICurry of the Prelude and emits its bytecode.  That cost about 1.5 s per
process on 2026-10-30 (0.3 to 0.55 s when first measured; the optimizer
passes that run over the Prelude's ICurry at load account for the
difference, issue #175); the compiled library objects avoid it.  So a
compiler-free installation that stayed in place should keep the library
objects that ``make stage`` compiled, and ``interpret:new`` is then the
cheaper explicit setting.

Adding a compiler later
=======================

Install ``g++`` (``sudo apt-get install g++`` on Debian and Ubuntu).  In a
source tree, configure CMake with ``-DWITH_CXX_POSTINSTALL=PATH``,
or let it find a C++ compiler on ``PATH``, and run ``make stage``: the staged
installation gets its ``tools/cxx``, and the next run without llvmlite compiles hot modules
in the background and swaps to the compiled code when the objects are
ready.  ``CMake WITH_CCACHE`` puts ccache in front of that compiler;
see :doc:`ConfiguringSprite`.  The conda package resolves the compiler of
its environment at run time through a ``tools/cxx`` wrapper of its own;
see ``conda/README.md``.
