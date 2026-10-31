.. _compilation-options:

===================
Compilation Options
===================

Curry code runs the way Python code does: import it and it runs.  Nothing
on this page needs to be configured for that.  The page is for the reader
who wants to know what happens behind the import, how to choose between
the interpreter, the just-in-time compiler and compilation ahead of time,
what each platform supports, and how to watch the choice at work.

Three ways to run a function
============================

Every Curry function reaches the runtime as ICurry, the intermediate
language of the compiler (:ref:`compilation-pipeline`).  The C++ runtime
can run it in three ways, with the same scheduler, the same rewrite steps
and the same answers:

Interpreted
  The runtime interprets a bytecode made from the ICurry when the module
  loads.  Nothing is compiled, and no compiler is needed.  This is how a
  freshly written module starts.

Compiled just in time
  A tier of the runtime compiles interpreted functions to machine code
  while the program runs and swaps the compiled code in at a safepoint of
  the scheduler.  Two backends do this: LLVM, through the Python package
  ``llvmlite``, compiles single functions in the process; the C++ backend
  writes the generated C++ of a module and compiles it with ``g++`` in a
  child process, then adopts the object.

Compiled ahead of time
  ``sprite-make --so M.curry`` compiles a module to a shared object beside
  its source, and ``make stage`` compiles the Curry library into the
  installation.  A current object loads whenever the module is imported,
  whatever the other settings say.  ``curry.save`` writes such an object,
  or a program around it, for use elsewhere (:doc:`PythonAPI/UsingTheAPI`).

The default combines them: current objects load, everything else starts
interpreted, and the functions that run often are compiled behind the
scenes.

The flags
=========

Three interpreter flags select the behaviour.  Set them for a process in
``SPRITE_INTERPRETER_FLAGS``, or for a session with ``curry.reset``
(:ref:`interpreter-flags`)::

    SPRITE_INTERPRETER_FLAGS=jit:off python -m curry Peano.curry

    >>> import curry
    >>> curry.reset(jit='eager', jit_backend='llvm')

===================  =====================  ================================================
Flag                 Values                 Meaning
===================  =====================  ================================================
``interpret``        ``new`` (default),     ``new`` loads current ahead-of-time objects and
                     ``all``, ``off``       interprets the rest.  ``all`` interprets every
                                            module and opens no object; it is the default
                                            on Windows.  ``off`` compiles a module that has
                                            no current object with ``g++`` before it runs.
``jit``              ``hot`` (default),     ``hot`` compiles an interpreted function after
                     ``eager``, ``off``     it has run ``SPRITE_JIT_THRESHOLD`` times (100).
                                            ``eager`` compiles every function of a module
                                            when the module loads.  ``off`` leaves the
                                            interpreter alone.
``jit_backend``      ``auto`` (default),    ``auto`` takes LLVM when ``llvmlite`` imports,
                     ``llvm``, ``gxx``      else ``g++`` when the installation has a C++
                                            compiler, else no backend.  A forced backend
                                            that is not available is an error at
                                            ``curry.reset`` or at the first import.
===================  =====================  ================================================

With no backend available and ``jit_backend:auto``, the process runs the
interpreter alone and says so once, as a warning.  The program still runs;
only its speed changes.

What is installed decides
=========================

The backends are optional.  What you install selects them:

- ``pip install --pre 'curry[jit]'`` adds ``llvmlite`` and with it the
  LLVM backend, on every platform that has a wheel for it.
- A C++ compiler on the machine (``g++``, or the compiler of Xcode) adds the
  ``g++`` backend and compilation ahead of time.  The installation records
  the compiler of its build; ``sprite-make`` uses the one it finds.
- Neither is needed to run Curry code: :doc:`Installation/WithoutCompiler`
  describes an installation with the interpreter alone.

==================  ===========  ===========  ==========  ======================
Platform            Interpreter  JIT: LLVM    JIT: g++    Ahead of time
==================  ===========  ===========  ==========  ======================
Linux x86-64        yes          yes          yes         yes
Linux aarch64       yes          yes          yes         yes
macOS arm64         yes          yes          yes         yes
macOS x86-64        yes          conda [1]_   yes         yes
Windows x64         yes          yes          no [2]_     no [2]_
==================  ===========  ===========  ==========  ======================

.. [1] ``llvmlite`` ships no wheel for Intel macOS on PyPI; the conda-forge
   package provides it.  Without it, ``auto`` takes ``g++``.
.. [2] No generated code is compiled on Windows: the runtime and its
   bindings build with clang-cl, but the compile of a Curry module to an
   object is not available there, so ``interpret`` defaults to ``all`` and
   the LLVM backend is the compiled mode.

Watching the choice
===================

Two environment variables turn on the log of the package
(:doc:`CommandLineInterface/EnvironmentVariables`).  At ``INFO`` the
package says what it decided for each module and for the process::

    SPRITE_LOG_LEVEL=INFO python -m curry Peano.curry

The lines name the backend chosen and why (``jit: backend llvm ...``, or
``jit: no backend, interpreter only ...``), each module as it loads
(``module Peano: compiled object loaded ...`` or ``module Peano:
interpreted ...`` with the reason: no object, a stale object, the
``interpret`` policy), the hot compiles (``jit hot: compiled ...`` with the
functions and the time; ``gxx hot: module ... compiled ... swapped``), the
product cache's hits and misses, and the runs of the front end.
``SPRITE_LOG_FILE`` sends the records to a file instead; child processes
write to the same file with their process id.

Two more variables serve the JIT itself: ``SPRITE_JIT_THRESHOLD`` sets the
number of calls that makes a function hot, and ``SPRITE_JIT_DUMP`` names a
directory into which the LLVM backend writes the optimized IR and the
assembly of each batch.

From Python, :data:`curry.flags` shows the flags of the session, and the
bindings of the runtime answer for a function::

    >>> from curry.backends.cxx import curryrtbindings as rt
    >>> rt.icurry_is_interpreted(M.f.info), rt.icurry_is_jit(M.f.info)

What comes next
===============

The stages between the Curry source and the bytecode are being redesigned
(October 2026): the ICurry of a module will be stored as a binary image
that the runtime reads directly, the optimizer passes will run once at
translation time, and the compiled code of the JIT will be cached beside
the module.  The flags of this page and the three ways to run a function
stay; the start of an interpreted module becomes much faster.  The plan
is recorded in the project's notes; the pipeline page describes the stages
as they are today.
