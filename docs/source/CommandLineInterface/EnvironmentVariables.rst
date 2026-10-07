.. highlight:: bash

Environment Variables
=====================

User Variables
--------------

Sprite's behavior can be controlled by setting certain environment variables.
The following are recognized:

``CURRYPATH``
  A colon-separated list of paths used to search for Curry modules.  Sprite
  silently appends to this the path to its system libraries.

``SPRITE_HOME``
  The installation tree of Sprite: the directory that holds ``bin``,
  ``curry``, ``lib``, ``python``, ``sysconfig``, and ``tools``.  The
  launchers under ``bin`` set it.  When it is not set, the Python package
  finds the tree from its own location, so ``import curry`` works with the
  package directory on ``PYTHONPATH``.

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
  too.  To compile a program without the warnings, say::

     SPRITE_FRONTEND_WARNINGS=0 sprite-make --so prog.curry

``SPRITE_GC_THRESHOLD``
  The number of nodes at which the collector of the C++ backend runs.  The
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
  collections, and it costs time on most programs, because a small heap
  stays in the cache.  The value is read when the runtime library loads.
  The Python backend does not use it.  To run the collector every 65536
  nodes, say::

     SPRITE_GC_THRESHOLD=65536 SPRITE_INTERPRETER_FLAGS=backend:cxx sprite-exec prog.curry

``SPRITE_GC_GROWTH``
  The growth factor of the collector of the C++ backend: after a
  collection, the next one runs when the heap reaches this many times the
  survivors, but not before the threshold.  The default is 8.  A value of
  2 keeps the heap within twice the live nodes and runs about three times
  as many collections.  The value must be at least 2 and is read when the
  runtime library loads.

  The default stays at 8 by a measurement of the memory suite of the
  benchmarks at 8, 12 and 16 (the dated TODO entry on G8, issue #83).  The
  factor touches a program only when the survivors of a collection exceed
  the threshold divided by the factor (131,072 nodes at growth 8 and
  65,536 at growth 16, with the default threshold), or when the live
  configurations exceed one eighth of that number, since the
  configuration threshold follows the same rule.  18 of the 29 programs
  measured kept their collections and their nodes marked exactly at every
  factor.  On the search programs with a live set near 300 MiB the trade
  is proportional, as the policy makes it.  Growth 16 halves the
  collections and the nodes marked (QueensSet9 11 to 6 collections,
  SearchQueens 19 to 10, PermSort 9 to 5).  It cuts the seconds of the
  collector by a quarter to a half, which is 1 to 8 percent of the CPU
  time of those programs and 1 to 3 percent of their instructions.  It
  costs 43 to 53 percent more peak RSS (QueensSet9 330 to 473 MiB,
  SearchQueens 307 to 465 MiB, PermSort 314 to 481 MiB), and the bound of
  the heap becomes sixteen times the live nodes in place of eight.  A
  user with memory to spare buys the saving with ``SPRITE_GC_GROWTH=16``.
  Growth 12 sits halfway on both sides of the trade.

``SPRITE_GC_STRESS``
  The stress mode of the collector of the C++ backend.  With the value
  ``1``, the collector runs at every safepoint of the scheduler: after
  every rewrite step of the outermost evaluation, and a nested set function
  hands the request outward.  A node that no root reaches is then reclaimed
  at the next step, so a missing root shows up at once, as a wrong value or
  a crash.  Every collection of the mode also runs the heap verifier, which
  checks every live node, its successors, and every node Python holds
  against the block heap and stops the process when the heap is
  inconsistent.  The mode costs a
  collection per step.  It is meant for the test suite (see
  ``tests/README``), not for a program.  The value ``0`` or an
  empty value turns the mode off, which is the default; another value turns
  it off with a warning.  The value is read when the runtime library loads.
  The Python backend does not use it.  To run the unit tests in stress
  mode, say::

     SPRITE_GC_STRESS=1 SPRITE_INTERPRETER_FLAGS=backend:cxx ./run_tests 'unit_*.py'

  A runtime built with the Memory Pool System (``make GC=mps``, an
  experiment) reads the three variables above with another meaning:
  ``SPRITE_GC_THRESHOLD`` runs a full collection every so many nodes in
  addition to the collections MPS schedules itself (unset: none),
  ``SPRITE_GC_GROWTH`` scales the configuration threshold after a full
  collection, and ``SPRITE_GC_STRESS`` runs a full collection at every
  safepoint, without a heap verifier.  ``SPRITE_GC_MPS_ARENA_MB`` (256),
  ``SPRITE_GC_MPS_NURSERY_KB`` (8192), and ``SPRITE_GC_MPS_GEN1_KB`` (65536)
  size its arena and its two generations.  See
  ``src/cyrt/graph/gc/mps.cpp``.

``SPRITE_GC_REPORT``
  With the value ``1``, every collection of the collector of the C++
  backend prints one line of ``key=value`` pairs on the standard error
  stream when it ends: its number, whether it ran inside a nested
  evaluation, the nodes before it and the survivors, the nodes marked (old
  and young apart), the seconds of its phases, the configurations pushed,
  the queues and configurations destroyed, the writes into old nodes since
  the collection before, the threshold it set, and the configurations,
  queues, sets and blocks alive.  The fields are those of ``sprite-exec
  --stats`` (``gc_marked`` and the others, without the prefix), per
  collection instead of summed.  The value ``0`` or an empty value turns
  the report off, which is the default; another value turns it off with a
  warning.  The value is read when the runtime library loads.  The Python
  backend does not use it.

.. _sprite-interpreter-flags:

``SPRITE_INTERPRETER_FLAGS``
  Overrides default flags in Sprite's Curry interpreter.  This can be set to a
  comma-separated list of colon-separated pairs (without spaces).  An item
  splits at its first colon, so ``rotation:time:10ms`` is one item.

  See the :mod:`list of flags <curry.interpreter.flags>` for details, and
  :ref:`interpreter-flags` for the table with the defaults.

  For example, to have Sprite generate debug code and print execution traces,
  set the following::

     SPRITE_INTERPRETER_FLAGS=trace:True,debug:True

  The ``backend`` flag selects the backend.  The C++ backend (``cxx``) is
  the default of an installation (``configure --with-default-backend``).
  The Python backend (``py``) suits small programs.  To run a program with
  it, say::

     SPRITE_INTERPRETER_FLAGS=backend:py sprite-exec prog.curry

  The ``interpret`` flag selects how the C++ backend runs a module without
  a compiled object: ``tiered`` (the default) interprets it and compiles it
  in the background, ``new`` interprets it and never compiles it, ``all``
  interprets every module, and ``off`` compiles every module first.  An
  installation without a C++ compiler runs under the default with one
  notice; see :doc:`/Installation/WithoutCompiler`.

  The ``step_budget`` flag sets the number of rewrite steps the Python backend
  gives one alternative before it moves to the next.  The default is 2048.
  The backend rotates only when another alternative waits, so a program with
  one alternative runs as before.  An alternative that overflows the Python
  stack runs again after the others.  When it overflows again without
  progress, it is dropped, and its error is reported after the others have
  run.  ``None`` disables the step-budget rotation.  Rotation on residuation
  and on Python stack overflow still occurs.  To change the budget, say::

     SPRITE_INTERPRETER_FLAGS=step_budget:65536 sprite-exec prog.curry

  The ``recursion_limit`` flag sets the number of Python frames the Python
  backend lets one value nest, the recursion limit of the interpreter while
  the value is computed.  The default is 262144.  The backend nests about
  eight frames per element of a list under a function that is not tail
  recursive, such as ``length`` or ``sort``, so the default covers a list of
  about thirty thousand elements; a larger limit costs about 4 KB of memory
  per nested element.  ``None`` leaves the limit of the interpreter as it
  is.  To raise the limit, say::

     SPRITE_INTERPRETER_FLAGS=recursion_limit:1048576 sprite-exec prog.curry

  The ``stack_limit`` flag sets the number of bytes of C stack the C++ backend
  lets one evaluation use.  The default is 4194304.  When an alternative
  reaches the limit, the backend unwinds to the scheduler and runs the other
  alternatives.  An alternative that cannot proceed within the limit is
  dropped, and its error is reported after the others have run.  A limit
  larger than the stack of the thread is clamped to that stack, less a margin
  of 1 MiB.  Set the flag to ``None`` to disable the guard.  To raise the
  limit, raise the stack size (``ulimit -s``) as well, and say::

     SPRITE_INTERPRETER_FLAGS=stack_limit:16777216 sprite-exec prog.curry

  The ``rotation`` flag selects how the C++ backend paces the rotation of
  its queue of alternatives.  The scheduler rotates at a safepoint, after a
  completed rewrite step, so a diverging alternative cannot starve the
  others.  In time mode, the default (``time:10ms``), a ticker thread sets
  one byte every quantum and the safepoint polls it; the latency of a
  waiting alternative is bounded by the quantum whatever a step costs.  In
  step mode (``steps:65536``) the safepoint counts the steps and rotates
  every N of them; the schedule then depends on the program alone, so the
  exact steps and forks of a search and the order of its values reproduce
  between runs.  A deterministic subcomputation never rotates in either
  mode.  In time mode two runs of a non-deterministic goal may print their
  values in a different order; to pin the order, set step mode::

     SPRITE_INTERPRETER_FLAGS=backend:cxx,rotation:steps:65536 sprite-exec prog.curry

  Time mode starts its thread at the first evaluation, so a host that forks
  after an evaluation is multi-threaded, and Python warns on ``os.fork`` in
  such a process; the forked child starts a ticker of its own at its first
  evaluation.  Step mode starts no thread.  ``SPRITE_ROTATION`` (below)
  sets the same flag alone.  The Python backend keeps its ``step_budget``
  and ignores the flag.

  The ``typed_expr`` flag selects the typed builder of :func:`curry.expr`.
  It is ``True`` by default.  With ``False``, ``curry.expr`` converts
  Python values by their Python type alone and supplies no class
  dictionaries, as :func:`curry.raw_expr` does, and ``exprtype`` is
  ignored.  The flag serves bisection::

     SPRITE_INTERPRETER_FLAGS=typed_expr:False install/bin/python script.py

``SPRITE_LOG_FILE``
  The file to which logging output is directed.  The default, ``-``, directs
  this to standard output.

``SPRITE_LOG_LEVEL``
  Sets the logging verbosity.  The **default** level is ``WARNING``.  Supported
  values are:

  - ``CRITICAL`` Log only critical (usually fatal) problems.
  - ``ERROR``    Log errors.
  - ``WARNING``  Log warnings.
  - ``INFO``     Log information about what Sprite is doing.
  - ``DEBUG``    Log detailed information about everything.

  Each of these includes all output from levels listed above it.

``SPRITE_ROTATION``
  The rotation mode of the C++ backend: ``time:10ms`` (time mode, the
  default; the unit may be ``s``, ``ms``, ``us`` or ``ns``) or
  ``steps:65536`` (step mode).  It sets the interpreter flag ``rotation``
  (above) below ``SPRITE_INTERPRETER_FLAGS``.  The test runner, the
  benchmark harness and the CI jobs set ``steps:65536`` through it, so
  that the counters of a run and the outputs of the tests reproduce; a
  value in the environment of a run wins.  An empty value counts as
  unset.  Other text is an error when the interpreter starts.  Time mode
  starts a thread at the first evaluation, so a host that forks after an
  evaluation is multi-threaded (Python warns on ``os.fork``); the forked
  child rotates with a ticker of its own.  Step mode starts no thread.  To
  run a search goal with the order of its values pinned, say::

     SPRITE_ROTATION=steps:65536 SPRITE_INTERPRETER_FLAGS=backend:cxx sprite-exec prog.curry

Development Variables
---------------------

Additional environment variables are recognized.  These are intended for people
developing Sprite itself.  If you plan only to compile and run Curry programs
with Sprite, then you should not need these.

``SPRITE_CACHE_FILE``
  Names the cache database, an SQLite file.  The database stores the output
  of the Curry front end, the :ref:`Curry to ICurry
  <Introduction/CompilationPipeline:Curry to ICurry>` step, which takes
  seconds per module.  An entry is keyed by a digest of the module source, of
  the sources of the modules it imports, of the front-end options, and of the
  route from Curry to ICurry (``SPRITE_CURRY2ICURRY``) with its program and
  flags.  The file name is not part of the key.  So the same text compiles
  once on a machine, from any directory and, for a module compiled from a
  string, under any module name.  A change in the text, or in an imported
  module, misses the cache.  A new front end misses it too, and an entry
  written by one route is never served to the other.  An error the front end
  reports about
  the program is cached as well; a failure of the environment is not, and
  neither is a missing module, because the key sees the Curry path only
  through the source files found in it.  An entry holds the ICurry of the
  module and the two interface files the front end wrote for it (``.fint``
  and ``.icurry``); a hit writes all three beside each other, so the types
  of a module are at hand without a run of the front end.

  A file name turns the cache on.  The empty string turns caching off.  When
  the variable is not set, the installation decides: ``configure --cache
  icurry`` or ``--cache all`` (``ENABLE_ICURRY_CACHE`` in ``Make.config``)
  turns the cache on at ``$HOME/.sprite/cache.db``.  The test drivers set
  the variable to ``tests/.cache/icurry.db``.  The database can also hold
  Sprite's
  :ref:`in-memory IR <Introduction/CompilationPipeline:JSON to Sprite IR>` of
  a JSON file (``ENABLE_PARSED_JSON_CACHE``).

  .. note ::
     Outside the test drivers, caching is off by default.

``SPRITE_CACHE_UPDATE``
  Specifies cache entries to update.  An entry of the ICurry cache is replaced
  on its own when its inputs change.  An update can still be needed for the
  parsed-JSON cache, or when a tool behind the front end changes without a
  change to the ``icurry`` program itself.  It is fine to simply delete the
  cache file in that case, but this method provides a more conservative
  option.

  Files matching the given pattern are updated in the cache database.  For
  the ICurry cache the pattern is compared with the name of the Curry source
  file, for the parsed-JSON cache with the name of the JSON file.  The pattern
  is interpreted as a glob unless it begins and ends with '/', as in
  ``/pattern/``, in which case it is considered a regular expression.

  Example:

      To update all compressed JSON files, set
      ``SPRITE_CACHE_UPDATE='*.json.z'`` in the environment.

``SPRITE_CURRY2ICURRY``
  Names the route from Curry to ICurry.  ``frontend`` runs the Curry front
  end and then Sprite's own translation from FlatCurry
  (:mod:`curry.toolchain.flat2icurry`).  ``icurry`` runs the Curry front
  end, then the ``icurry`` program, when ``configure`` was given
  ``--with-icurry``; both routes need the front end.  The default is the
  choice made by ``configure`` (option ``--curry2icurry``), else the front
  end.  Both routes write the same files.

``SPRITE_CXX_PCH_ROOT``
  The directory under which the C++ backend keeps the precompiled form of the
  runtime header that every generated module includes.  The default is the
  ``include`` directory of the installation, where the compiler finds it
  without an extra flag.  When that directory cannot be written, or when the
  installation lies in a conda environment (a directory with a ``conda-meta``
  entry above it), the default is a directory of the user's cache instead:
  ``$XDG_CACHE_HOME/sprite/pch/<key>``, or ``~/.cache/sprite/pch/<key>``,
  where the key is a digest of the real path of the installation.  So a
  package is not written at run time.  The cache keeps one directory of
  about 70 MB per installation and removes none of them; the directory
  ``pch`` may be deleted at any time, and the header is built again on the
  next compile.  Set the variable to the empty string to compile without
  the precompiled header.  The header is built again when it is older than
  any header file.

``SPRITE_DEBUG``
  Enables debugging for Sprite internal errors.  The command-line tools
  :ref:`sprite-exec` and :ref:`sprite-make` normally report unexpected errors
  tersely.  Enabling this allows one to see the full stack trace when Sprite
  fails.  Set this to the value ``1`` to enable debugging.

``SPRITE_DISABLE_SYSLIB_CHECKS``
  When the variable is set, Sprite skips the check of the system libraries,
  the Prelude and the other modules of ``curry/`` in the installation.  The
  check finds each of them on the Curry path and confirms that no file
  earlier on the path shadows it.  Without the variable a missing or
  shadowed system library ends the process with a message that names the
  paths.

``SPRITE_ENABLE_BREAKPOINT``
  When the variable is set, ``import curry`` installs a ``breakpoint``
  hook of Sprite's own (``sys.breakpointhook``), an interactive prompt in
  the frame of the call, and the built-in ``pdbtrace``, which starts PDB.
  For the development of Sprite itself.

``SPRITE_FORCE_RECOMPILE_CXX``
  When the variable is set, the C++ backend leaves the generated C++ file
  and the shared object of a module out of the prerequisites it compares,
  so every module is generated and compiled again whatever their times
  say.

``SPRITE_WORKTREE_ROOT``
  The directory under which ``scripts/new-worktree.sh`` puts the install
  and object trees of a new git worktree; the default is
  ``~/.cache/sprite/worktrees``.

Test Variables
--------------

The test runner (``tests/run_tests``; section 10 of ``tests/README``) sets
the environment of every test file: ``SPRITE_HOME``, ``SPRITE_CACHE_FILE``
(``tests/.cache/icurry.db``), ``SPRITE_INTERPRETER_FLAGS`` (the backend of
the run), ``SPRITE_ROTATION=steps:65536`` unless the environment of the
run names a mode, and ``SPRITE_FRONTEND_WARNINGS=0`` unless the environment
sets it.  Three variables address the tests themselves:

``SPRITE_TEST_MAX_VMEM_KB``
  The cap on the address space of a test process, in KiB, or
  ``unlimited``.  The runner keeps the cap as a backstop behind its
  memory budget (6 GB, or three times the cap of the file, whichever is
  larger); the other drivers under ``tests/`` cap every process at 6 GiB.

``SPRITE_TEST_FLAGS``
  Interpreter flags that the CI script ``.github/scripts/run-tests.sh``
  appends to ``SPRITE_INTERPRETER_FLAGS`` for the files of a shard; the
  nightly job runs the suites under ``interpret:all`` and
  ``interpret:off`` through it.

``SPRITE_UPDATE_EXPECTED``
  With the value ``1``, ``tests/unit_examples.py`` writes the output of
  each run script of ``examples/`` to its ``expected.out`` instead of
  comparing with it; run it once per backend and review the diff.

Build Variables
---------------

These are variables of ``make``, read when Sprite is built.  ``Make.config``
describes them beside the settings of ``configure``.

``SPRITE_REBUILD_ICY``
  ``make stage`` derives the JSON of a library module from its committed
  ``.icy`` file and never translates the module again.  With
  ``SPRITE_REBUILD_ICY=1`` it runs the front end and the translation again
  and writes a new ``.icy``; the committed files are pinned artifacts of
  the front end of PAKCS 3.4.1 and of ``icurry`` 3.1.0, so this is a
  deliberate step.

``DEBUG=1``
  The debug flavor of the runtime: the assertions on, no optimization.
  The C++ backend compiles the modules of an interpreter whose flag
  ``debug`` is set in the same flavor.

``TRACE=1``
  Computation tracing in the C++ runtime (``SPRITE_TRACE_ENABLED``).

``COUNTERS=1``
  The scheduler counters of the C++ runtime (``SPRITE_SCHEDULER_COUNTERS``),
  reported by ``sprite-exec --stats``; see :ref:`sprite-exec`.

``GC=mps``
  The Memory Pool System in place of the default collector, an experiment
  behind a gate; the ``SPRITE_GC_*`` variables above change their meaning
  under it.

``GC_WRITE_COUNTERS=1``
  The counters of the writes into old nodes (``SPRITE_GC_WRITE_COUNTERS``),
  the four ``gc_old_*`` fields of ``--stats``.  They are part of the ABI
  stamp, so a switch compiles every module again.

``JOBS=N``, ``PREFIX=DIR``
  The job count of the build (``configure --jobs``) and the directory of
  ``make install``.
