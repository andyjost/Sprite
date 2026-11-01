Environment Variables
=====================

User variables
--------------

Environment variables select the behavior of Sprite. Sprite reads the
following:

``CURRYPATH``
  A colon-separated list of paths used to search for Curry modules.  Sprite
  silently appends to this the path to the Curry library.  A program
  given as a file (``sprite-exec Peano.curry``, ``sprite-make --so
  Peano.curry``, ``curry.import_(path)``) has its
  directory searched first, before the entries of CURRYPATH, as PAKCS
  searches: the modules beside the program are found without a CURRYPATH
  that names their directory.  A module given by name is searched on
  CURRYPATH alone.  A hierarchical name ``A.B`` resolves to ``A/B.curry``
  beside an optional ``A.curry``; a user module with a library module's
  name is refused with a message naming both files.

``SPRITE_JIT_CACHE``
  A writable per-user directory for LLVM JIT objects when the module's
  attached image directory is read-only. Entries live at
  ``<Full.Name>/<key>.jit`` (the function index and batch objects together).
  An unset or empty value disables this fallback. Writable image
  directories always keep their object beside ``M.img``. ``jit:off``
  reads and writes neither location. Objects may be deleted at any time;
  the JIT compiles again on a miss. Windows persistence is not available.

``SPRITE_HOME``
  The installation tree of Sprite: the directory that holds ``bin``,
  ``curry``, ``include``, ``lib``, ``licenses``, ``python``, ``sysconfig`` and ``tools``.  The
  launchers under ``bin`` set it.  When it is not set, the Python package
  finds the tree from its own location, so ``import curry`` works with the
  package directory on ``PYTHONPATH``.
  A failed library check raises ``ImportError`` with the reason.

``SPRITE_FRONTEND``
  The command or path of the Curry front end. It overrides the installed
  tool link, the script beside Python and PATH. An empty value disables
  the front end. :doc:`/Installation/ConfiguringSprite` gives the lookup
  order.

``SPRITE_FRONTEND_WARNINGS``
  The Curry front end warns on overlapping rules ("Function f is
  potentially non-deterministic due to overlapping rules"), under which
  ``build 0 = ...; build n = ...`` compiles to a choice whose second
  alternative is infinite.  A run of the front end (an import, a compile
  from text, ``sprite-make``) reports that warning once per module
  through the log at the WARNING level, with the text of the front end;
  the other warnings of the front end stay quiet.  The value ``0`` (or
  ``off``, ``no``, ``false``) silences the warnings for the process; any
  other value, or none, leaves them on, and an empty value counts as
  unset.  ``sprite-make -q`` silences them as well.  The test runner, the
  test library and the benchmark harness set the variable to ``0``, so
  the output of a suite does not depend on which modules a run compiles;
  the run scripts of the examples whose rules overlap by design set it
  too.  To compile a program without the warnings::

     SPRITE_FRONTEND_WARNINGS=0 sprite-make --so Peano.curry

``SPRITE_GC_THRESHOLD``
  The number of nodes at which the collector of the runtime runs.  The
  default is 1048576, about 30 MB of nodes in the block heap of the
  runtime.  The allocator checks the count once per run of free slots, so
  a collection comes within a few thousand nodes of the threshold.  After
  a collection the
  threshold is eight times the survivors, but not less than the configured
  value, so the heap stays within eight times the live nodes.  The
  collector also runs when the live configurations of the scheduler reach
  one eighth of the node threshold, with the same growth rule: a set
  function consumed only in part leaves its queue to the collector.  A
  lower value keeps the heap smaller.  A higher value runs fewer
  collections and it costs time on most programs, because a small heap
  stays in the cache.  The value is read when the runtime library loads.
  To run the collector every 65536 nodes::

     SPRITE_GC_THRESHOLD=65536 sprite-exec Peano.curry

``SPRITE_GC_GROWTH``
  The growth factor of the collector of the runtime: after a
  collection, the next one runs when the heap reaches this many times the
  survivors, but not before the threshold.  The default is 8.  A value of
  2 keeps the heap within twice the live nodes and runs about three times
  as many collections.  A value below 2 falls back to the default with a warning. The value is
  read when the runtime library loads.

  Growth 16 halves the collections of the search programs, saves 1 to 8
  percent of their CPU time and costs about half again as much peak memory.
  Growth 12 sits between.

``SPRITE_GC_REPORT``
  With the value ``1``, every collection of the collector of the C++
  backend prints one line of ``key=value`` pairs on the standard error
  stream when it ends: its number, whether it ran inside a nested
  evaluation, the nodes before it and the survivors, the nodes marked (old
  and young apart), the seconds of its phases, the configurations pushed,
  the queues and configurations destroyed, the writes into old nodes since
  the collection before, the threshold it set and the configurations,
  queues, sets and blocks alive.  The fields are those of ``sprite-exec
  --stats`` (``gc_marked`` and the others, without the prefix), per
  collection instead of summed.  The value ``0`` or an empty value turns
  the report off, which is the default; another value turns it off with a
  warning.  The value is read when the runtime library loads.

.. _sprite-interpreter-flags:

``SPRITE_INTERPRETER_FLAGS``
  Interpreter flags as comma-separated colon pairs, without spaces. Each
  pair overrides its flag's default. An item splits at its first colon,
  so ``rotation:time:10ms`` is one item. :ref:`interpreter-flags` gives the
  defaults and :doc:`/CompilationOptions` describes execution modes.
  To compile modules in the debug flavor::

     SPRITE_INTERPRETER_FLAGS=debug:true sprite-exec Peano.curry

  ``stack_limit`` defaults to 4194304 bytes on the caller's stack;
  ``worker_stack`` defaults to a 1 GiB reservation for deep evaluations.
  ``rotation`` defaults to ``time:10ms``. Step mode pins the order of
  answers (:ref:`interpreter-flags`).

``SPRITE_JIT_THRESHOLD``
  The number of calls that makes an interpreted function hot; 100 by
  default. With ``jit:hot`` (the default), LLVM compiles that function;
  the C++ compiler backend starts the module's child compile when its first
  function becomes hot. ``jit_backend:auto`` selects llvmlite, then the installation's C++
  compiler, then the interpreter alone with one warning. Force ``llvm``
  or ``cxx`` to require that backend; ``jit:off`` disables both tiers.

``SPRITE_LOG_FILE``
  Enable logging and append records to this path; ``-`` selects standard
  error. With neither logging variable set, the Python logger ``curry`` has
  only a ``NullHandler``. Setting either variable at import configures one
  real handler, without propagation to Python's root logger or configuring it.
  Each record uses the format
  ``%(asctime)s %(levelname)s %(process)d %(name)s: %(message)s``.
  The process ID distinguishes children writing to the same file.

``SPRITE_LOG_LEVEL``
  The minimum severity, case-insensitive: ``DEBUG``, ``INFO``, ``WARNING``,
  ``ERROR`` or ``CRITICAL``. The default is ``WARNING``; an unknown name
  stops the import with an error. Setting this variable alone enables a
  handler on standard error at that level. Setting only ``SPRITE_LOG_FILE``
  enables a file handler at ``WARNING``. At ``INFO``, Sprite reports interpreter
  flags and the installation, compiled or interpreted module loads and
  their reasons, background compile results, cache hits and misses,
  the timing of the front end and warning counts, rewrite decisions and ICurry and
  image writes. ``DEBUG`` adds stamp differences and tool command lines.
  Existing ``CurryWarning`` notices also reach the log at ``WARNING``.
  With neither variable set, notices keep their existing display through
  ``warnings.warn`` on standard error.

``SPRITE_ROTATION``
  The queue rotation mode: ``time:10ms`` (default) or ``steps:65536``.
  It sets ``rotation`` below ``SPRITE_INTERPRETER_FLAGS``; an empty value
  is unset. The test runner and benchmark harness use step mode to pin
  answer order and counters::

     SPRITE_ROTATION=steps:65536 sprite-exec Peano.curry

Developer, test and build variables are in :doc:`/DevelopmentVariables`.
