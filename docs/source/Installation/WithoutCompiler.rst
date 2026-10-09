.. _without-compiler:

=============================================
Installing and running without a C++ compiler
=============================================

The C++ backend, the default of Sprite, needs a C++ compiler for one thing:
to compile a Curry module to a shared object.  The runtime library
``libcyrt``, its Python bindings, and the Curry front end need no compiler
at run time.  A module without a compiled object runs interpreted: the
runtime interprets the ICurry of the module from a bytecode, on the same
scheduler and with the same rewrite steps as compiled code (the interpreter
flag ``interpret``; see :mod:`curry.interpreter.flags`).  So an
installation without a C++ compiler runs every Curry program.

The build itself needs the compiler: ``configure`` finds ``g++``, and
``make stage`` compiles the runtime library and the Curry library.  An
installation without a compiler is one that moved to another machine, or a
package such as the conda package of ``conda/README.md`` installed without
``cxx-compiler``.  Sprite looks for its compiler at ``tools/cxx`` under
``SPRITE_HOME``; when that file is missing, the installation has none.

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
another path.  Under the default of the flag
``interpret``, ``tiered``, a module without a current object is interpreted
at once.  With a compiler, a child process compiles the module in the
background, and the runtime swaps its functions to the compiled code when
the object is ready.  Without one, the module stays interpreted, nothing is
compiled, and no object is written.  The first time this happens in a
process, Sprite prints one notice on the standard error stream::

    [WARNING] no C++ compiler is installed at .../tools/cxx; module 'Peano' and the modules after it run interpreted (add interpret:new to SPRITE_INTERPRETER_FLAGS to select the interpreter without this notice)

The notice names the setting of the flag that selects the interpreter
without a compile.  Where the library loaded compiled and no generated
file lies beside the ICurry of the module, as here, it names
``interpret:new``, which keeps the compiled library.  On an installation
that moved, the module the notice names is the Prelude: every library
object is stale, the whole program runs interpreted, and the notice names
``interpret:all``.

The other settings of the flag:

``interpret:all``
    Every module is interpreted, the library included, and no compiled
    object is used.  This is the explicit setting of an installation
    without a compiler: it never compiles, so it serves an installation
    that moved as well, and it silences the notice.  It is also the mode
    under which the test suites run the interpreter (section 4 of
    ``tests/README``).

``interpret:new``
    No background compile and no notice: a module with a current object
    loads compiled, a module without one is interpreted.  A module whose
    object is stale is compiled, which fails without a compiler, so this
    setting suits an installation whose library objects are current, one
    that stayed in place, and not one that moved.

``interpret:off``
    Every module is compiled before it runs.  Without a compiler the run
    fails with an error that names the remedy: ``cannot compile ...: no C++
    compiler is installed at .../tools/cxx.  Install one and configure
    Sprite with --with-cxx-postinstall, or use the modules that make stage
    compiled.``

The flags are set in ``SPRITE_INTERPRETER_FLAGS``; see
:doc:`/CommandLineInterface/EnvironmentVariables`.

The cost
========

The interpreter takes about 1.1 to 1.5 times the time of compiled code for
the evaluation of a program (the measurements are in the ``TODO`` entries
on issues #31 and #64).  A process that interprets the Prelude, under
``interpret:all`` or when the library objects are missing, first reads the
ICurry of the Prelude and emits its bytecode.  That costs about 0.3 to
0.55 s per process; the compiled library objects avoid it.  So a
compiler-free installation that stayed in place should keep the library
objects that ``make stage`` compiled, and ``interpret:new`` is then the
cheaper explicit setting.

Adding a compiler later
=======================

Install ``g++`` (``sudo apt-get install g++`` on Debian and Ubuntu).  In a
source tree, run ``configure`` again with ``--with-cxx-postinstall=PATH``,
or let it find ``g++`` on ``PATH``, and run ``make stage``: the staged
installation gets its ``tools/cxx``, and the next run compiles the modules
in the background and swaps to the compiled code when the objects are
ready.  ``configure --with-ccache`` puts ccache in front of that compiler;
see :doc:`ConfiguringSprite`.  The conda package resolves the compiler of
its environment at run time through a ``tools/cxx`` wrapper of its own;
see ``conda/README.md``.
