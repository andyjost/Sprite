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

``SPRITE_GC_THRESHOLD``
  The number of nodes at which the collector of the C++ backend runs.  The
  default is 1048576, about 50 MB of nodes.  After a collection the
  threshold is eight times the survivors, but not less than the configured
  value, so the heap stays within eight times the live nodes.  A lower
  value keeps the heap smaller.  A higher value runs fewer collections, and
  it costs time on most programs, because a small heap stays in the cache.
  The value is read when the runtime library loads.  The Python backend
  does not use it.  To run the collector every 65536 nodes, say::

     SPRITE_GC_THRESHOLD=65536 SPRITE_INTERPRETER_FLAGS=backend:cxx sprite-exec prog.curry

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
  the sources of the modules it imports, and of the front-end options.  The
  file name is not part of the key.  So the same text compiles once on a
  machine, from any directory and, for a module compiled from a string, under
  any module name.  A change in the text, or in an imported module, misses the
  cache.  A new front end misses it too.  An error the front end reports about
  the program is cached as well; a failure of the environment is not, and
  neither is a missing module, because the key sees the Curry path only
  through the source files found in it.

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
