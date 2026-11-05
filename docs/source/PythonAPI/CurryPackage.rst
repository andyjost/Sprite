=====================
The ``curry`` Package
=====================

.. _top-api:

The :download:`installed public stub <../../../src/python/__init__.pyi>`
records the public names and their signatures. :doc:`UsingTheAPI` describes
the builders, value classes and session operations.

The top-level names, including ``curry.eval`` and ``curry.import_``, are
methods of a global interpreter created at import.
``Interpreter(flags={...})`` from ``curry.interpreter`` starts another
session. Its initial flags follow the same order: defaults,
``SPRITE_ROTATION``, ``SPRITE_INTERPRETER_FLAGS``, then the argument.

Fork the process only while Sprite has no evaluation, compilation, queued or
running JIT work or native handle operation in any thread; an idle child starts fresh
workers and synchronization state without cleaning up the parent's resources.
A child forked while Sprite is busy raises ``curry.exceptions.ForkError`` on
later Sprite calls and when a callback returns into the interrupted evaluation;
if that callback runs on the large-stack worker, the child reports the error to
standard error and exits with status 1.

.. _interpreter-flags:

Interpreter flags
=================

:data:`curry.flags` is a read-only mapping of the current session's flags.
The environment variable ``SPRITE_INTERPRETER_FLAGS`` sets the initial
flags of a process (``interpret:off,rotation:steps:65536``).  Use
``curry.reset(**flags)`` to start a new session with other flags.  Reset retains ``curry.path`` and makes earlier
terms stale.  ``curry.reload(module, text=...)`` replaces a module's code;
it does not set interpreter flags.  The docstring of ``curry.interpreter.flags``
(``help(curry.interpreter.flags)``) describes every flag at length; the table names them with their defaults.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Flag
     - Default
     - What it changes

   * - ``backend``
     - ``cxx``
     - The runtime selector; only ``cxx`` is accepted.

   * - ``interpret``
     - ``new``
     - ``new`` loads current objects and interprets the rest; ``all`` interprets every module; ``off`` compiles missing objects before running.

   * - ``jit``
     - ``hot``
     - Interpreted functions compile at load (``eager``), after the hot threshold (``hot``) or stay interpreted (``off``). Current ahead-of-time objects still load.

   * - ``jit_backend``
     - ``auto``
     - ``auto`` selects llvmlite, then a C++ compiler, then the interpreter alone with one warning. Forced ``llvm`` and ``cxx`` error when unavailable.

   * - ``rotation``
     - ``time:10ms``
     - How the runtime paces the rotation of its queue of alternatives: time mode (``time:<N><unit>``) or step mode (``steps:<N>``), in which the order of the values of a search reproduces.  ``SPRITE_ROTATION`` sets it alone.

   * - ``stack_limit``
     - ``4194304``
     - Bytes of C stack one evaluation may use on the calling thread; ``None`` disables the guard.

   * - ``worker_stack``
     - ``1073741824``
     - The retained worker's stack reservation in bytes; ``None`` disables escalation for deep evaluations.

   * - ``inline_budget``
     - ``4``
     - The largest function body, in nodes built, that the optimizer inlines at a call; a call of a single-case function on a constructor becomes the branch.  ``0`` turns both rules off.

   * - ``checker``
     - ``False``
     - The checker mode of the Fair Scheme proofs program: the runtime asserts the run-time invariants of the Fair Scheme at every fork, escape, pull-tab, instantiation and yield.

   * - ``debug``
     - ``False``
     - More consistency checks; the runtime compiles its modules in the debug flavor.

   * - ``trace``
     - ``False``
     - Reserved; runtime traces require a ``TRACE`` build.

   * - ``keep_temp_files``
     - ``False``
     - Keep the temporary files; a string names the directory for them.

   * - ``postmortem``
     - ``False``
     - Copy the generated code of a failed compile from a string to the working directory.

``recursion_limit``, ``step_budget``, ``lazycompile`` and
``telemetry_interval`` are accepted and have no effect.

``curry.path`` includes ``CURRYPATH``, local CPM sources and the installed
library. See :ref:`curry-packages` for discovery and ``curry.cpm_path``.
