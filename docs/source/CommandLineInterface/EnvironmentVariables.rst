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

``SPRITE_INTERPRETER_FLAGS``
  Overrides default flags in Sprite's Curry interpreter.  This can be set to a
  comma-separated list of colon-separated pairs (without spaces).

  See the :mod:`list of flags <curry.interpreter.flags>` for details.

  For example, to have Sprite generate debug code and print execution traces,
  set the following::

     SPRITE_INTERPRETER_FLAGS=trace:True,debug:True

  The ``backend`` flag selects the backend.  The Python backend (``py``) is
  the default.  It suits small programs.  To run a program with the C++
  backend, say::

     SPRITE_INTERPRETER_FLAGS=backend:cxx sprite-exec prog.curry

  The ``step_budget`` flag sets the number of rewrite steps the Python backend
  gives one alternative before it moves to the next.  The default is 2048.
  The backend rotates only when another alternative waits, so a program with
  one alternative runs as before.  An alternative that overflows the Python
  stack runs again after the others.  When it overflows again without
  progress, it is dropped, and its error is reported after the others have
  run.  ``None`` disables the step-budget rotation.  Rotation on residuation
  and on Python stack overflow still occurs.  To change the budget, say::

     SPRITE_INTERPRETER_FLAGS=step_budget:65536 sprite-exec prog.curry

  The ``stack_limit`` flag sets the number of bytes of C stack the C++ backend
  lets one evaluation use.  The default is 4194304.  When an alternative
  reaches the limit, the backend unwinds to the scheduler and runs the other
  alternatives.  An alternative that cannot proceed within the limit is
  dropped, and its error is reported after the others have run.  A limit
  larger than the stack of the thread is clamped to that stack, less a margin
  of 1 MiB.  Set the flag to ``None`` to disable the guard.  To raise the
  limit, raise the stack size (``ulimit -s``) as well, and say::

     SPRITE_INTERPRETER_FLAGS=stack_limit:16777216 sprite-exec prog.curry

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
  (:mod:`curry.toolchain.flat2icurry`).  ``icurry`` runs the ``icurry``
  program, when ``configure`` was given ``--with-icurry``.  The default is
  the choice made by ``configure`` (option ``--curry2icurry``), else the
  front end when it is installed.  Both routes write the same files.

``SPRITE_CXX_PCH_ROOT``
  The directory under which the C++ backend keeps the precompiled form of the
  runtime header that every generated module includes.  The default is the
  ``include`` directory of the installation, where the compiler finds it
  without an extra flag.  Name another directory when the installation is
  read-only.  Set the variable to the empty string to compile without the
  precompiled header.  The header is built again when it is older than any
  header file.

``SPRITE_DEBUG``
  Enables debugging for Sprite internal errors.  The command-line tools
  :ref:`sprite-exec` and :ref:`sprite-make` normally report unexpected errors
  tersely.  Enabling this allows one to see the full stack trace when Sprite
  fails.  Set this to the value ``1`` to enable debugging.
