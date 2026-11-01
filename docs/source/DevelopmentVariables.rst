Development Variables
=====================

These variables serve the development, tests and builds of Sprite.
:doc:`CommandLineInterface/EnvironmentVariables` lists the variables for
running programs.

.. _CommandLineInterface/EnvironmentVariables:Development Variables:

Compiler and runtime variables
------------------------------

``SPRITE_GC_STRESS``
  The stress mode of the C++ runtime collector.  With the value
  ``1``, the collector runs at every safepoint of the scheduler: after
  every rewrite step of the outermost evaluation and a nested set function
  hands the request outward.  A node that no root reaches is then reclaimed
  at the next step, so a missing root shows up at once, as a wrong value or
  a crash.  Every collection of the mode also runs the heap verifier, which
  checks every live node, its successors and every node Python holds
  against the block heap and stops the process when the heap is
  inconsistent.  The mode costs a
  collection per step; ``tests/README`` describes its use in the suite.  The value ``0`` or an
  empty value turns the mode off, which is the default; another value turns
  it off with a warning.  The value is read when the runtime library loads.
  Run the unit tests in stress mode::

     SPRITE_GC_STRESS=1 ./run_tests 'unit_*.py'

``SPRITE_JIT_DUMP``
  A directory into which the LLVM backend writes the optimized LLVM IR
  and assembly of each batch. It has no effect on the C++ compiler backend.

``SPRITE_CACHE_FILE``
  Names the cache database, an SQLite file.  The database stores the output
  of the Curry front end, the :ref:`Curry to ICurry
  <CompilationPipeline:Curry to ICurry>` step, which takes
  seconds per module.  An entry is keyed by a digest of the module source, of
  the sources of the modules it imports, of the options of the front end and of the
  route from Curry to ICurry (``SPRITE_CURRY2ICURRY``) with its program and
  flags.  The file name is not part of the key.  So the same text compiles
  once on a machine, from any directory and, for a module compiled from a
  string, under any module name.  A change in the text or in an imported
  module misses the cache.  A new front end misses it too and an entry
  written by one route is never served to the other.  An error the front end
  reports about
  the program is cached as well; a failure of the environment is not, and
  neither is a missing module, because the key sees the Curry path only
  through the source files found in it.  An entry holds the ICurry of the
  module and the two interface files the front end wrote for it (``.fint``
  and ``.icurry``); a hit writes all three beside each other, so the types
  of a module are at hand without a run of the front end.

  A file name turns the cache on.  The empty string turns caching off.  When
  the variable is not set, the installation decides: CMake ``ENABLE_ICURRY_CACHE=ON``
  turns the cache on at ``$XDG_CACHE_HOME/sprite/cache.db``, or
  ``$HOME/.cache/sprite/cache.db`` when ``XDG_CACHE_HOME`` is unset or empty.
  This is beside the precompiled headers and worktrees in the user's cache
  directory.  The test drivers set
  the variable to ``tests/.cache/icurry.db``.

  Without the variable and without ``ENABLE_ICURRY_CACHE``, caching is off.

``SPRITE_CACHE_UPDATE``
  Curry-source patterns whose ICurry cache entries are replaced. Patterns are globs or regular expressions when surrounded by
  slashes. For example, ``SPRITE_CACHE_UPDATE='*.curry'`` replaces all
  matching entries. Changed inputs invalidate entries automatically.

``SPRITE_CURRY2ICURRY``
  Names the route from Curry to ICurry.  ``frontend`` runs the Curry front
  end and then Sprite's own translation from FlatCurry
  (:mod:`curry.toolchain.flat2icurry`).  ``icurry`` runs the Curry front
  end, then the ``icurry`` program, when CMake was given
  ``-DWITH_ICURRY=PATH``; both routes need the front end.  The default is the
  choice made by CMake (``CURRY2ICURRY_TOOL``), else the front end.  The runtime route uses Sprite's translation; compatibility mode is checked
  against independent ``icurry`` output.

``SPRITE_CXX_PCH_ROOT``
  The directory under which the runtime keeps the precompiled form of the
  runtime header that every generated module includes.  The default is the
  ``include`` directory of the installation, where the compiler finds it
  without an extra flag.  When that directory cannot be written or when the
  installation is a wheel or lies in a conda environment (a directory with a ``conda-meta``
  entry above it), the default is a directory of the user's cache instead:
  ``$XDG_CACHE_HOME/sprite/pch/<key>`` or ``~/.cache/sprite/pch/<key>``,
  where the key is a digest of the real path of the installation.  So a
  package is not written at run time.  The cache keeps one directory per installation and removes none of them; the directory
  ``pch`` may be deleted at any time and the header is built again on the
  next compile.  Set the variable to the empty string to compile without
  the precompiled header.  The header is built again when it is older than
  a header the generated code includes (the include closure of
  ``curryrt/curryrt.hpp``).  A header outside the closure never makes it stale.

``SPRITE_DEBUG``
  The full traceback of an internal error.  :ref:`sprite-exec` and
  :ref:`sprite-make` report an unexpected error in one line; with the
  value ``1`` they print the Python traceback.

``SPRITE_DISABLE_SYSLIB_CHECKS``
  When the variable is set, Sprite skips the check of the Curry library,
  the Prelude and the other modules of ``curry/`` in the installation.  The
  check finds each of them on the Curry path and confirms that no file
  earlier on the path shadows it.  Without the variable a failed library
  check raises ``ImportError`` with the reason and the paths.

``SPRITE_ENABLE_BREAKPOINT``
  When the variable is set, ``import curry`` installs a ``breakpoint``
  hook of Sprite's own (``sys.breakpointhook``), an interactive prompt in
  the frame of the call and the built-in ``pdbtrace``, which starts PDB.
  For the development of Sprite itself.

``SPRITE_FORCE_RECOMPILE_CXX``
  When the variable is set, the runtime leaves the generated C++ file
  and the shared object of a module out of the prerequisites it compares,
  so every module is generated and compiled again whatever their times
  say.

``SPRITE_PRODUCT_CACHE``
  The directory of the compiled product cache. An unset or empty value
  disables it. ``sprite-make``, background C++ compiles and the test
  prepare pass restore current objects, generated C++ and ABI stamps
  before compiling, then store new products. The key covers content,
  runtime ABI, flags and imported interfaces; it names no tree.
  The test runner uses ``tests/.cache/products`` and prunes other runtimes
  after preparation. The cache grows and can be deleted. A run prints
  ``sprite-make: product cache: N restored, M stored`` when it used the
  cache. ``toolchain/_productcache.py`` documents the key and publication.

``SPRITE_WORKTREE_ROOT``
  The directory under which ``scripts/new-worktree.sh`` puts the install
  and object trees of a new git worktree; the default is
  ``~/.cache/sprite/worktrees``.

``SPRITE_WORKTREE_PREPARE``
  With the value ``1``, ``scripts/new-worktree.sh`` ends with the prepare
  pass of the test runner on the runtime (``tests/run_tests
  --prepare-only``), which compiles the shared Curry products of the test
  pool into the new worktree and stores them in the product cache.  The
  script never copies the compiled products of the main tree: their ABI
  stamps name the installation of that tree.  A product cache the two
  trees share serves the worktree the products of the main tree.

Test variables
--------------

The test runner (``tests/run_tests``; section 10 of ``tests/README``) sets
the environment of every test file: ``SPRITE_HOME``, ``SPRITE_CACHE_FILE``
(``tests/.cache/icurry.db``), ``SPRITE_PRODUCT_CACHE``
(``tests/.cache/products``) unless the environment names it,
``SPRITE_INTERPRETER_FLAGS`` (the flags of the run),
``SPRITE_ROTATION=steps:65536`` unless the environment of the run names a
mode and ``SPRITE_FRONTEND_WARNINGS=0`` unless the environment sets it.  Three variables address the tests themselves:

``SPRITE_TEST_MAX_VMEM_KB``
  The cap on the address space of a test process, in KiB, or
  ``unlimited``.  The runner keeps the cap as a backstop behind its
  memory budget (6 GB or three times the cap of the file, whichever is
  larger); the other drivers under ``tests/`` cap every process at 6 GiB.

``SPRITE_TEST_FLAGS``
  Interpreter flags that the CI script ``.github/scripts/run-tests.sh``
  appends to ``SPRITE_INTERPRETER_FLAGS`` for the files of a shard; the
  nightly job runs the suites under ``interpret:all`` and
  ``interpret:off`` through it.

``SPRITE_UPDATE_EXPECTED``
  With the value ``1``, ``tests/unit_examples.py`` writes the output of
  each run script of ``examples/`` to its ``expected.out`` instead of
  comparing with it; run it once and review the diff.

Build variables
---------------

These are build settings. Pass CMake options as ``-DNAME=value``; the thin
Makefile also accepts the historical variables below. See
:doc:`Installation/ConfiguringSprite`.

``SPRITE_STAGE_JIT_CACHE``
  Set to ``0`` to skip the fill of the library's persistent LLVM JIT cache at
  ``make stage``. Otherwise a local stage fills it when llvmlite is available.
  Wheels omit persistent JIT objects. CI enables the fill in one default C++
  shard only.

``SPRITE_REBUILD_ICY``
  ``make stage`` derives the module image of a library module from its committed
  ``.icy`` file and never translates the module again.  With
  ``make stage SPRITE_REBUILD_ICY=1`` it runs the front end and the translation again
  and writes a new ``.icy``; the committed files are pinned products of Sprite's translation of
  the FlatCurry that front end 3.1.0 (PAKCS 3.10.0) writes. The independent
  ``icurry`` 3.3.0 outputs are the oracles under ``tests/overlay/``. The legacy pair compiles its library from source and
  does not reuse these pins.

``DEBUG=1``
  The debug flavor of the runtime: the assertions on, no optimization.
  The runtime compiles the modules of an interpreter whose flag
  ``debug`` is set in the same flavor.

``TRACE=1``
  Computation tracing in the C++ runtime (``SPRITE_TRACE_ENABLED``).

``COUNTERS=1``
  The scheduler counters of the C++ runtime (``SPRITE_SCHEDULER_COUNTERS``),
  reported by ``sprite-exec --stats``; see :ref:`sprite-exec`.

``GC=mps``
  A runtime built with the Memory Pool System (``make GC=mps``, an
  experiment, off by default) reads the three variables above with
  another meaning:
  ``SPRITE_GC_THRESHOLD`` runs a full collection every so many nodes in
  addition to the collections MPS schedules itself (unset: none),
  ``SPRITE_GC_GROWTH`` scales the configuration threshold after a full
  collection and ``SPRITE_GC_STRESS`` runs a full collection at every
  safepoint, without a heap verifier.  ``SPRITE_GC_MPS_ARENA_MB`` (256),
  ``SPRITE_GC_MPS_NURSERY_KB`` (8192) and ``SPRITE_GC_MPS_GEN1_KB`` (65536)
  size its arena and its two generations.  See
  ``src/curryrt/graph/gc/mps.cpp``.

``GC_WRITE_COUNTERS=1``
  The counters of the writes into old nodes (``SPRITE_GC_WRITE_COUNTERS``),
  the four ``gc_old_*`` fields of ``--stats``.  They are part of the ABI
  stamp, so a switch compiles every module again.

``JOBS=N``, ``PREFIX=DIR``
  The job count of the build and the directory of
  ``make install``.
