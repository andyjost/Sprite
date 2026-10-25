===============
Developer Notes
===============

This page holds the facts a developer of Sprite needs and a user does not.

.. _free-threaded-audit:

Free-threaded Python
====================

The C++ extension opts in with ``pybind11::mod_gil_not_used()`` (vendored
pybind11 3.1.0). The supported C++ API permits threads to import modules,
build terms, evaluate and consume separate results concurrently. The runtime
serializes its process-wide heap: two evaluations still step one at a time
per heap, while Python work outside native metadata/heap operations can run
in parallel on a free-threaded interpreter. Parallel Curry execution is epic
#28 and is outside this work.

``PYTHON_GIL`` belongs to the user. Package children inherit its presence or
absence and its value. The 3.14t CI lane runs the unit suites with
``PYTHON_GIL=0`` and the concurrency suite again with the variable absent;
the suite checks the actual GIL state after importing the extension. This
lane remains ``continue-on-error`` until the reviewer observes two green
runs. No free-threaded interpreter is available for local verification.

The table inventories shared state used by the C++ Python API. Python
builders, converters, parsers and compiler instances keep their working
state private to each operation. Published type descriptions, compiler
specification tables and constants are immutable by convention. Direct
mutation of private/raw backend structures is not an additional concurrent
API. Tests run on the ordinary interpreter too; its GIL cannot establish
absence of races with the GIL disabled.

Audit of shared state
---------------------

.. list-table::
   :header-rows: 1
   :widths: 16 22 27 35

   * - State
     - Location (under ``src/python``)
     - Hazard
     - Protection

   * - Singleton and hard reload
     - ``__init__.py; interpreter.__init__``
     - Replacing a session and bound exports could mix old/new interpreter state; temporary environment flags leaked between threads.
     - Public functions resolve the interpreter once per call; flags/modules are live read-only views. Hard reload retires/publishes under a native metadata transaction and passes flags explicitly, without changing the environment. Initial imports use Python import serialization.

   * - Session, reset, reload and flags
     - ``interpreter/{__init__,session,flags}.py``
     - Reset/retirement overlapped native materialization; clear/update exposed incomplete settings or module metadata.
     - Reset and reload native/publication phases share the existing heap gate, with tiered waits outside. Settings are validated privately and published as a new dict. Reload builds privately and updates complete metadata without clearing mandatory slots; it retains module identity. Tokens/versions enforce the stale rule. FLAG_INFO/defaulting tables are immutable after initialization.

   * - Paths and streams
     - ``interpreter/session.py; config.py; toolchain/_system.py``
     - Temporary path/environment changes affected another compilation.
     - Imports take path snapshots. Literate-source scope and child CURRYPATH are ContextVars; subprocesses get copied environments. The public path list retains its API. Stream references publish by assignment; Python stream objects provide their own I/O synchronization.

   * - Module registry and packages
     - ``interpreter/import_/``
     - A provisional module could escape before symbols/classes were complete; two builders could race native tables.
     - Dependencies prepare outside the native metadata phase. A context-local provisional registry supports recursive symbol resolution. Under the heap gate, construction rechecks the session and existing module and publishes a complete canonical module; only the registry/parent update uses the short interpreter lock. Code generation keeps only its bootstrap module private and preserves real dependency imports.

   * - Python import hook
     - ``lib/__init__.py; interpreter/session.py``
     - Reset could evict a name before Python finished publishing an old-session module; duplicate hooks could install.
     - A short hook-registry lock tracks names/deduplicates hooks. Python owns sys.modules publication. Reset snapshots tracked names and acquires each Python module-name lock before eviction, without holding the heap or a Sprite mutex while waiting.

   * - Anonymous names and expression keepalive
     - ``interpreter/compile.py``
     - Concurrent name allocation and registry/keepalive updates could overlap.
     - A small counter lock allocates process-unique names. Registry removal and keepalive append use the interpreter metadata lock; no native call or evaluation is inside that lock. Reset retires the session under the heap gate.

   * - Backend instances and retired libraries
     - ``backends/__init__.py; backends/cxx/interface.py``
     - Check/create could publish competing backend singletons; retirement must retain borrowed native names/types.
     - Construct backends outside the singleton lock and publish with setdefault. Retirement runs in native session transactions; the retained-library list is append-only under that gate. Backend objects are stateless after construction.

   * - Native object loader
     - ``backends/cxx/loader.py``
     - Conflicting-file checks, open/adoption and _objects publication could interleave.
     - Dependency imports and background waits precede the native metadata transaction. File identity/stamp is rechecked after imports and at native entry; changed products retry. Registry checks/open/adoption/publication share heap ownership. No Python loader lock spans a native wait.

   * - Tiered state
     - ``backends/cxx/tiered.py``
     - Bindings/jobs/records/modules/private directories/warnings/counter updates could overlap poll, submit, cancellation or reset.
     - Native metadata transactions serialize these updates with their native operations. Job waits remain outside transactions and poll between bounded waits. Temporary names share the gate. No Python mutex transfers to the large-stack worker.

   * - First-use materialization and bytecode
     - ``backends/cxx/materialize.py``
     - _PENDING, table check/create/attach and compile/adopt could race; eager preparation would move errors.
     - Materialization and pending-registry operations use heap metadata transactions. The trap already owns the heap through compilation/adoption; lazy first-use semantics remain. BYTECODE values are complete before publication and read by a single dictionary lookup; published bytecode is immutable.

   * - Product locks
     - ``toolchain/_productlock.py``
     - The process-wide _held bypass treated a competing thread as the owner.
     - Per-path RLock ownership plus flock; recursion is thread-local. Registry entries are reference-counted while in use. Fork callbacks close inherited descriptors and reset locks; unwinding an inherited context does not release a parent lock. Existing unwritable/no-flock fallback retains thread exclusion and atomic publication.

   * - Generated source and objects
     - ``toolchain/_makecurry.py; backends/{generic,cxx}/toolchain.py; materialize.py``
     - Product-lock -> heap inverted the trap order; direct writes/unlinks exposed partial or absent products.
     - Import/render/link-command preparation happens before the file lock. Sources, objects and stamps publish through unique temporary names and rename. A contender accepts a current product another producer published. Plans advance their own pipeline instead of reselecting stale later products between stages. A reader rechecks identity/stamp after importing dependencies.

   * - Product cache and pruning
     - ``toolchain/_productcache.py``
     - Replacement removed paths used by readers; concurrent counters lost increments.
     - Entries are immutable, first-producer-wins directories published by rename. A thread/process lock beside the cache root covers store/restore/prune; restore pins the entry for placement. A separate counter lock protects updates/resets. Forced rebuilds still replace local products, retaining a published cache entry of the same content key.

   * - Creation permissions
     - ``cache.py; toolchain/_productcache.py``
     - Reading umask by temporarily setting it to zero changed process-wide state.
     - Exclusive temporary-file creation with mode 0666 and directory creation with mode 0777 obey the real umask without changing it. Native products and PCH files use unique temporary names.

   * - SQLite and source memo
     - ``cache.py``
     - One connection had thread affinity; reset could close a connection still in use; memo/stat updates raced.
     - Thread-local connections and a reset generation; in-progress transaction slots retain their connection. Slots are local to their creating toolchain transaction/thread. A memo RLock protects pure memo construction and counters. SourceInfo objects are read-only snapshots.

   * - Configuration lazy values
     - ``config.py``
     - Lazy reads and cached-list reset/publication could overlap.
     - A configuration RLock covers initialization and path reset; currypath returns a copied list. Published scalars are immutable. No native heap entry occurs under the config lock.

   * - Signature tables and interfaces
     - ``typecheck/sigtable.py; exprtype.py``
     - Lazy interface/decoded/scheme/instance caches, weak callbacks and clear/purge could overlap.
     - Interface-cache/decode locks and a per-table RLock protect publication. Resolve module names and native symbol tags before taking the table lock. Weak callbacks remove matching entries under the same lock. Returned instance maps are snapshots; schemes/decoded declarations/synonyms are read-only after publication.

   * - Type records and symbol maps
     - ``typecheck/builder.py; terms.py``
     - Node identity, weak cleanup and cache construction could race or reuse an id.
     - Resolve native node identity outside the record lock; protect record updates/weak callbacks. Interpreter publication creates one record. Symbol maps build from one registry snapshot and publish a complete tuple/map. Type-variable ids use a counter lock; inference/unification cells are private to each problem.

   * - Module wrappers and constructor classes
     - ``objects/terms.py; classes.py``
     - Lazy wrapper caches could publish competing objects; incomplete classes could escape.
     - ModuleInfo cache locks cover Python-only wrapper construction. Classes/fields finish before module publication and are immutable for that version. Reload prepares complete replacements and updates owner references before publication. Raw-symbol selection remains a ContextVar.

   * - Shared free variables and iterator payloads
     - ``expressions.py; typecheck/builder.py; objects/terms.py``
     - Shared-node check/create and inferred types could race; iterator cursor weak entries could disappear.
     - Shared node/owner publish as one tuple; node check/create and external-freevar counters use native metadata transactions. A marker lock commits compatible inferred types with pure unification. Cursor weak-registry updates/callbacks have their own lock. IteratorSource buffers/cursor consumption run in serialized C++ Python-generator callbacks under the heap gate; conversion state belongs to one evaluation.

   * - Results and Stream
     - ``objects/results.py; interpreter/eval.py``
     - Concurrent next/close could corrupt iterator ownership; deferred evaluation could start after reset.
     - A short per-iterator lock claims a busy flag, released before stepping/callbacks; overlapping use keeps Python generators' existing ValueError behavior. Cleanup runs under that claim. Deferred results/streams check their creation session before starting and on both sides of each native step. Separate results can be consumed concurrently.

   * - Evaluation statistics
     - ``backends/generic/eval/evaluator.py; interpreter/stats.py``
     - Finalization could double-count a running evaluation in a snapshot or lose totals.
     - A totals lock covers Python counters/weak registry and its version. Native counter reads happen outside the lock; version changes retry the snapshot. Direct single_step accounting remains supported. Returned stats are private snapshots, not a global pause of all activity.

   * - Compilation time, warnings and parser caches
     - ``toolchain/_makecurry.py; _curry2icurry.py; flat2icurry/interfaces.py; backends/cxx/toolchain.py``
     - Overlapping compiles were mistaken for nesting; memo/counter/warning publication could race.
     - Thread-local compile nesting/start with locked accumulation. Short locks cover rewrite statistics/warnings and compiler warning sets. FlatCurry caches publish complete read-only trees with setdefault; finder instances are private. PCH files publish atomically with unique names; digest lru_caches use standard-library synchronization.

   * - Temporary directories and dispatch/type factories
     - ``toolchain/_str2module.py; utility/{visitation,proptree}.py``
     - Set iteration and lazy class/handler-order construction could race.
     - Directory snapshots and updates share a short lock. Dynamic class factories have registry locks. Dispatch ordering computes from a handler snapshot outside its lock and publishes an immutable tuple only if the registered types still match; handlers run after releasing locks.

   * - Binding trap hook
     - ``backends/cxx/curryrtbindings/module.cpp``
     - A process-global py::object was reassigned/invoked; attaching Python thread state is not exclusion.
     - set_trap_hook already uses heap_access; invocation already runs under the locked rewrite step. Retain a local callable reference across reentrant replacement. Its process-lifetime storage intentionally avoids Python teardown destruction; this is not a subinterpreter opt-in.

   * - Binding literals, constants and graph lifetime
     - ``backends/cxx/curryrtbindings/{icurry,graph,dynload,tiered}.cpp; heap.hpp``
     - Literal-map check/allocate/insert, graph/registry access and native destruction need exclusion without a GIL.
     - Literal maps are accessed under icurry_attach heap_access; small literal/opcode/constants initialize before module publication and then stay immutable. Existing heap_access, HeapScope, rooting and HeapDeleter cover graph/native lifetime and return conversion. Callbacks attach thread state; waits/steps detach it. The runtime lock is unchanged.

File publication and lock order
-------------------------------

First use remains lazy: a trapped function compiles when it is first called,
and unused functions do not move compilation failures earlier. There is no
product-lock-to-heap edge. Importing dependencies, materializing native
symbols, rendering source and preparing the linker command precede the
file-production lock. The lock covers only producing/rechecking/publishing
files. A producer writes a unique temporary name and publishes by rename;
another producer that finds a current published product takes it. Failed
compilation retains the previous published object and stamp. Publication
invalidates the old stamp, renames the completed object, then publishes its
new stamp; a missing stamp makes the object stale.
The ICurry sidecar, generated C++ and ABI stamp record imported interface
digests (and imported ICurry for C++ inlining), so changed imports make
the corresponding products stale too.

A reader checks a product before importing its dependencies and rechecks
its file identity/stamp afterward, retrying if a producer replaced it.
Restore similarly releases file locks before consulting interpreter/native
state. Cache entries are immutable and first-producer-wins; a separate
thread/process lock pins store/restore/prune operations. Lock order there
is module product lock, then cache-root lock. No cache-root lock leads to
an interpreter import or native heap entry. An external deletion of an
entire cache is handled as a miss/I/O failure, as before.

The trap hook already holds the heap and may take a product lock. The
reverse order does not exist. Python interpreter/cache/counter mutexes are
short metadata locks: no such mutex is held while waiting for the native
heap or evaluating. Native metadata transactions acquire the existing heap
gate first and group the associated native operations and registry
publication. Dependency preparation and job waits are kept outside those
transactions. Evaluation itself is never enclosed in a Python mutex or a
metadata transaction. The large-stack worker therefore requires no Python
lock ownership transfer.

Regression coverage is in ``tests/unit_free_threading.py``: complete module
publication, concurrent imports/builds/consumption, cross-thread reset and
staleness, Python import-hook eviction, two-process/two-thread cache writes,
thread-owned product locks, a forced producer under a reader, and a trapped
first use while another producer prepares native imports. Existing
``unit_evaluation_lock.py`` and ``unit_issue153.py`` cover reentrant callbacks
and the worker handoff. The source-tree implementation/validation report is
``CODEX-REPORT.md``.

.. _reference-backend:

Removal of the reference backend
================================

The Python backend was removed on 2026-10-24 at the owner's word (B4,
issue #82, stage 6).  The C++ runtime is the one runtime, including its
interpreter for installations without a compiler.  The earlier evaluator,
generated Python form, debugging aids and migration stages are documented
in the Git history before this removal and in issue #82.

The checker mode
----------------

The interpreter flag ``checker`` (off by default) turns on the checker of
the run-time invariants of the Fair Scheme, the checker mode of section 6.5
of the memo on the Fair Scheme proofs.  The runtime state holds one
``Checker`` of
``src/curryrt/checker.hpp`` (``RuntimeState::checker``, a pointer that is null
otherwise).  Every hook in a runtime is one test of that attribute or
pointer, so the flag-off path costs one test per event and makes the same
steps, values and counters as before, and the checker changes no step, no
value and no counter when it is on; it costs time, and memory, since it
keeps every flagged cell alive for the life of the runtime state.  A
violation raises ``InvariantViolation``, an ``AssertionError`` whose
message names the invariant, the event, the configuration (its queue, its
set, its fingerprint, its groups, its root), the identifiers and the goal
position; on the C++ backend the class is
``curry.backends.cxx.curryrtbindings.InvariantViolation``, raised from the
hook through the scheduler as the step limit is.  To run a program under
the checker::

   SPRITE_DEBUG=1 SPRITE_INTERPRETER_FLAGS=backend:cxx,checker:true sprite-exec prog.curry

``sprite-exec`` prints an ``AssertionError`` as "an internal error
occurred" unless ``SPRITE_DEBUG=1`` is set, so the report of a violation
needs that variable under ``sprite-exec``; the Python API raises the
exception with its full message.

The hooks sit at the events the memo names, and each one runs the checks
of the invariants it names (``RI`` numbers the invariants of the review of
the implementation; the memo states them in its sections 2.1 to 2.5):

* A fork (``rts_fingerprint.fork``) and a yield (``rts_control.
  release_value``): the fingerprint of the configuration is a function and
  its group invariant holds (every decided identifier agrees with the root
  of its group, and no member disagrees), the fingerprints along the
  dispatch chain of the nested queues agree, and the escape sets only grow
  (B1, S0).  Each clone of a fork keeps every decision of its parent, has
  the decision of the fork, and adds at most the forked identifier and its
  group root (rule D.2 of the memo; a fork on a free variable, which
  applies its bindings, may add more).  A fork inside a capsule is on an
  identifier that is function-derived for the capsule, that is in the
  escape set of no enclosing capsule and that no enclosing configuration
  decided, or on one its queue was split on before (S0, def:s-escapes).
  At a yield no choice, operation, failure or constraint cell is reachable
  from the value, no bound variable remains in it, and for every variable
  with a decided root identifier the identifiers on the decided path of
  its generator are decided (B1, X-c).  Two exclusions, which the paper
  must carry: the walk does not enter the generator of a free variable,
  and it does not enter the arguments of a partial application, as the
  walk of ``N`` does not (a value may hold ``(+) (1 ? 2)`` as a function
  value with the choice unevaluated inside it).  At a fork, at a yield and
  at a constraint step at the root (rule D.beta) as well: a decided class
  of two or more variables has a generator at its root (E5, Def 2.74 of
  the note on the Fair Scheme; issue #127), and every binding sits under
  the root of its class, one binding per class (E11, Remark 2.70; issue
  #128), and no class holds a variable that lies inside the generator
  instance of another member (D15 (occurs check), the decision of
  2026-10-12: the union that would make such a class fails the step).
  At a constraint step as well: a binding the step dropped at the merge
  of two bound classes is guarded, above the result of the step, by its
  strict equality with the binding kept (D26 (guard at the merge), the
  decision of 2026-10-12).
* The dispatch of a configuration and a drop of it (``D``, and ``N`` at a
  failed successor of the root): the discards change no cell, so a
  constructor, set-guard or constraint cell at the root holds at the drop
  the symbol and the successors, through forward cells, it held at the
  dispatch (Def 2.40 (discard); issue #126 of the C++ scheduler).
* A slot write of an existing generator (``hnf``) and an instantiation
  inside a step of ``=:=`` or ``=:<=``: the step narrows a variable that
  is free in the configuration against a constructor alone; two free
  variables make a constraint cell, and a free left side of ``=:<=`` takes
  the right side as a binding without a step at it (Def 2.62 (equality
  step); issue #129).  A step of ``=:=`` that meets a decided variable and
  a variable that is free in the configuration records the pair: it
  neither narrows the free one against the instance nor replaces the
  decided one by its generator (decision D25 of 2026-10-12).
* An escape, rule SF.1 (``rts_setfunctions.split_queue``): the escaping
  identifier is argument-derived for the capsule or for an enclosing one,
  or an enclosing configuration decided it; the kept queue holds the LEFT
  and the undecided configurations, the new one the RIGHT and the
  undecided, both record the identifier, and both name one escape set
  (S0, S-split).  An insertion into an escape set (a pull-tab across a
  box) is of an argument-derived identifier (S0).
* A pull-tab (``rts_fingerprint.pull_tab``): the created choice carries the
  identifier of its source, the source is at the recorded path, and the
  two alternatives are fresh copies of the spine that share the cells off
  the path (B1); the identifier is in the escape set of every box the path
  crosses (S0, def:s-pull).
* An instantiation, rule S.x (``rts_freevars.instantiate``), a generator
  (``_make_generator``) and the private copy of rule N.x (``N`` and
  ``hnf``): one generator per variable with the variable's identifier at
  its root (X1); the write is a faithful copy of the spine with the
  generator at the end, and the reduct of every configuration that
  references the redex, read under the fingerprint it is compatible with,
  is the same before and after the write; the reduct of the private copy
  equals the reduct of the root it replaces (X-b').  The reduct is read
  with the generator image of the memo (a decided choice is its side, a
  bound variable its binding or its generator, a free variable its
  group) and compared through a digest, within a budget of cells per
  event; an event over the budget is counted, not compared.
* A step (``fairscheme.S``, after a completed step): the choice a step
  creates is tagged with the boxes above it, the set guards crossed from
  the root of each configuration of the dispatch chain to the redex, and
  the capsules whose arguments reached the redex (the entry walk of a
  capsule flags the cells reachable from its arguments, up to 50000 cells
  per capsule, and the cells a step, a pull-tab, a copy or a generator
  creates at a flagged cell inherit the flags, up to 1024 cells per event;
  the walk of a step starts at the successors of the result cell, since
  the redex itself carries the flags already, and a walk over its budget
  makes the sets of the flags unbounded, so their checks of S0 are
  suppressed from then on, as after an entry walk over its budget; a leaf
  value, a constructor or a failure without a successor cell, is not
  flagged).  The tags define
  "argument-derived" for the checks of S0.  A replacement
  by failure comes from an exempt leaf of the definitional tree of the
  operation, or from a built-in (B2).
* An inductive position (``fairscheme.hnf``, at entry): the position is a
  case of the definitional tree of the operation at the redex, rebuilt
  from the ICurry case structure, under branches that match the
  constructors already at the positions above it (B2).  B2 is asserted
  for the operations with an ICurry body alone.  The built-in steps of
  ``currylib`` are hand-written Python outside the generated code, have
  no tree and are not checked; they are most of the ``hnf`` calls of a
  run (on the set-function and functional-pattern goals of the suite,
  10773 of 16492 calls: ``plusInt``, ``nonstrictEq``, ``apply``, ``cond``,
  ``eqChar``, ``allValues``, ``_biString``, ``&``, ``constrEq``,
  ``ltEqInt``, ``evalS``, ``applyS``, ``set``, ``$!``, ``eqInt`` lead).

``tests/unit_py_checker.py`` holds one constructed violation per check and
runs the known-good programs of the suite under the checker.  The checker
does not check the lifts of the constraints of ``=:=`` and ``=:<=`` (the
memo's FS-β), the schedule replay of section 6.5, or the private copies
that a set function makes for a configuration.  "Argument-derived" is read
from the tags of an identifier (the boxes above its creation site and the
flags of the capsule's arguments), which over-approximate the escape sets:
the checks of the current capsule read the tags, the checks of the
enclosing capsules read the escape sets, as def:s-escapes does.

The checker of the runtime (``src/curryrt/checker.hpp``,
``src/curryrt/checker.cpp``) mirrors the Python checker hook by hook and check
by check.  Its header is outside the include closure of ``curryrt/curryrt.hpp``:
the generated code never sees it, and the hooks reach the checker through
the pointer of the runtime state.  The hooks sit at the same events: the
fork (``rts_fingerprint.cpp``, after the clones went into the queue and
before the parent leaves it), the escape (``allValues_step`` of
``currylib/setfunctions.cpp``, around ``Queue::split``), the pull-tab
(``RuntimeState::pull_tab``, before the copies of the spine and after the
choice over them), the yield (``release_value``), the fresh variable
(``freshvar``), the generator (``_make_generator`` and
``clone_generator``), the value bindings and the private copies of rule N.x
(``replace_freevar``), the write of a generator into a slot (rule S.x:
``instantiate``, and the slot write of an existing generator in
``replace_freevar``), the step (``procS``, before and after the step
function) and the inductive position (``hnf``, at entry), the entry of a
capsule (``evalS_step``), the record of a failure in a capsule
(``RuntimeState::record_failure``) and the end of a capsule on the empty
queue (``allValues_step``).  The checker reads the state without changing
it: the union-find without path compression, the fingerprints without the
growth of ``check_alloc`` (it enumerates the used bits of the blocks of
the tree), the bindings without the absorption of ``get_binding``.  It
keeps alive, as roots of the collector, every cell it flags and one box of
every capsule it enters, so that the addresses in its tables stay those of
the objects they name (the table of the generators compares addresses
alone and roots nothing); under the MPS collector it also clamps the arena
for the life of the runtime state.  The checks of B1 at a fork cost the
same along a long chain of narrowings, where the Python checker reads
every entry of the fingerprint: the group invariant is read over the ids
the union-find united, the dispatch chain only inside a capsule, and rule
D.2 from a diff of the clone's fingerprint tree against its parent's that
skips the blocks the two share.  The group check rests on an invariant of
``UnionFind``: ``unite`` is the only writer of its data and appends both
ids to the list ``united``, so every member of a group of two or more is
in the list (the collector reads it for the same reason).  A writer that
bypassed ``unite`` would silence the check; ``test_group_invariant_at_fork``
reads the list.  The comparison of the reducts at a write
of rule S.x is skipped for a lone configuration (one queue of one
configuration, no capsule entered), which alone references the redex.  A
private copy of rule N.x whose slot is not a level of the scan is reported
as a violation of X-b' (``copy_spine`` copies the levels of the scan from
the slot down, so such a slot is a defect of the copy, not a case the check
can skip); no program of the suite reaches it.

Where the two checkers differ:

* B2 is checked for the operations the ICurry interpreter of the runtime
  runs: the definitional tree is rebuilt from the bytecode of the
  operation (``BIND_ROOT`` and ``BIND_VAR`` give a variable its position,
  ``COPY_VAR`` an alias, ``STORE_VAR`` a value that is not a position,
  ``CASE_CONS`` and ``CASE_LIT`` the cases) at its first use and kept, so
  an operation the tiered mode swaps to compiled code afterwards keeps its
  tree.  A compiled operation has no bytecode and no tree: under
  ``interpret:off``, and under ``tiered`` for a module loaded from its
  object, the ``hnf`` calls of the generated step functions are counted as
  untracked (``hnf_untracked``), not checked.  A compiled check would need
  the tree from another source: the bytecode kept beside the compiled step
  (the swap clears ``aux`` today), the ICurry of the module handed down
  from the Python side when the flag is on, or a tree table the emitter
  writes into the object.  Under ``interpret:all`` every operation with an
  ICurry body is checked.  The measure, on the 165 known-good goals of the
  test file (one runtime state per goal, ``steps:65536``): under the tiered
  default after the prepare pass of the runner, 411 of 66545 ``hnf`` calls
  are checked (0.6%; the rest are compiled steps and built-ins), under
  ``interpret:all`` 22254 of 66538 (33.4%; the rest are the built-ins of
  ``currylib``, which have no tree on either backend).  A run that checks
  B2 on the C++ backend therefore uses
  ``backend:cxx,checker:true,interpret:all``; the tiered pair exercises
  the compiled steps under the other invariants.
* A replacement by failure has three sources in the runtime.  An exempt
  leaf is one.  A failure at an inductive position is a completed step
  (``hnf`` forwards the redex to the failure and the step returns), and
  the check accepts it (B2 c names it).
  A return of a reference (``RET_REF``) forwards the redex to the node the
  reference denotes, which may be a failure; the tree tells such a leaf
  from the return of a built node, and the check accepts it.
* The write of rule S.x is a write into the slot of the variable
  (``*slot = genexpr``), not a copy of the spine, so the check is the
  memo's X-b (Inst-slot): the reduct of every configuration that references
  the redex is read before the write and compared after it, and no flags
  propagate (no cell is made).  The slot write of a generator that exists
  already (the ``has_generator`` branch of ``replace_freevar``) is checked
  the same way (``slot_writes`` in the
  counts).  The reduct of a configuration with a binding of the variable
  reads the generator choice of the variable as the binding, as it reads
  the variable itself: the fork applies the binding to the generator.
* The configurations whose reducts are compared are those of the queues of
  the dispatch chain and of the capsules their graphs reach (the SetEval
  nodes the walk meets), not every queue the collector registers: the
  registry also holds the queues of other evaluations and of unloaded
  interpreters, whose nodes this evaluation must not read.  A capsule
  reachable from a yielded value alone is not read.
* The reduct of a variable without a generator of its own, decided through
  its group, is the generator of the representative of the group: that is
  the node the runtime puts into the copy of rule N.x (``get_generator``
  reads it by the group id).
* The private copies that a set function makes for a configuration
  (``evalS_step``, the clone of a capsule) are not checked.

One false alarm was shared by the two checkers, found in the review of the
C++ mirror and fixed on 2026-10-09.  The step propagation of the flags was
a no-op on the runtime: the walk started at the redex, which carries the
flags, and stopped there, so a cell a step made at a flagged redex
inherited nothing (the pull-tabs, the copies and the generators
propagated).  The consequence: a boxed argument whose evaluation outside
the box, after the capsule started, creates a choice got a false report of
S0 (E in A) at the pull-tab across the box, on the runtime.  The program
(``lazyThenOutside2`` of the test files)::

   g2 n = case n of { 1 -> Just (A ? B); _ -> Nothing }
   f2 x = 0 ? (case x of Just y -> case y of { A -> 1; B -> 2 })
   lazyThenOutside2 = let a = g2 (length [()]) in
     let vs = valuesOf (set1 f2 a) in (head vs, fromJust' a, vs)

The capsule yields 0 without demanding ``a``; the enclosing configuration
steps ``g2`` at the flagged cell, then ``?``, whose choice carried the tags
of the boxes above it and the flags of the ``?`` cell, which were none; the
second alternative of the capsule pulls the choice across the box.  The
runtime gives ``(0, A, [0, 1])`` and ``(0, B, [0, 2])``, the values of
weakly encapsulated search.  The walk of a step starts at the successors
of the result cell now (``Checker::step_end`` propagates from the result,
when the step forwarded the redex to a fresh cell, and from each successor
of the result, under the budget of one walk; ``Checker.step`` propagates
from the successors of the node), so the ``?`` cell inherits the flags of
the redex of ``g2`` and the choice is argument-derived for the box.
``TestSharedArgument`` of both test files pins the values under the
checker on three shapes (``lazyThenOutside2``, ``twoCapsulesChoice2`` with
two capsules over the argument, ``capturedThenShared2`` with the argument
captured by a second set function), and the known-good goals of both files
report nothing with the same counts as before.

The walk of a step is bounded by 1024 cells.  A step whose result holds
more cells than that (``bigThenOutside`` of the test files: the step of
``gBig`` builds a list of 100 elements of about 23 cells each) leaves the
far cells without the flags, so a choice made there outside the box
carries no tag, and the pull-tab across the box would be reported.  A walk
over its budget therefore makes the sets of the flags unbounded, as the
entry walk does: the event is counted (``propagate_over_budget``) and the
checks of S0 of those sets are suppressed from then on.  The budget is a
policy of the instrumentation, not of the invariants.

``tests/unit_cxx_checker.py`` runs the known-good programs under the
checker, compiled and under ``interpret:all``, with the values and the
counters they have without it, and provokes one violation per check
through the debug entry points of the bindings
(``curryrtbindings.checker_debug_*``), which corrupt one configuration of a
runtime state on purpose or run one check on constructed nodes; the
entries refuse while the flag is off.  ``curryrtbindings.checker_counts``
gives the counts of the events a state saw.

The depth bounds of the toolchain
=================================

A deep expression, such as the nest of cons calls of a long literal list
or a chain of nested if-then-else, met a recursive walk at every stage of
an import.  Issue #125 made the walks of the route from Curry to ICurry
iterative (``utility.trampoline`` and explicit stacks), and pothole batch 4
(2026-10-10) the walks of the import after it: the visitor of the
optimizer (``icurry.visit``), the copy of a function body and the other
walks over an expression in the inliner (``icurry.analysis.inlining``;
``copy.deepcopy`` of a call or a choice copies the nested calls and
choices on a stack of its own), the rewrite of the saturation pass
(``interpreter.optimize``) and the expression compiler of the runtime
(``backends.generic.compiler.compileE``).  A literal list of 10800
elements imports and runs on the runtime under ``interpret:new``
(``tests/unit_curry2icurry.py``, ``TestDeepExpressions``; about 9 s on
the C++ backend).  What still bounds a deep expression, as measured on the
machine of that lane:

* The JSON codec of the ICurry (``icurry.json``) recurses in C, in the
  codec of Python.  A nest of 12000 calls is written and read back; one of
  15000 overflows the 8 MB stack of the main thread (``RecursionError``,
  "Stack overflow").  The bound is a bound in levels of nesting of the
  ICurry, not in frames of Python, so ``maxrecursion`` does not move it; a
  thread with a larger stack, or a codec without the recursion, would.

* The monadic analysis (``icurry.analysis.monadic``) follows the call
  graph: a chain of nested if-then-else lifts into a chain of functions,
  one per level, and the analysis recurses once per function, four frames
  per level (``set_monadic_metadata``, ``visit``, the visitor and
  ``_checkmonadic``; 506 levels under a limit of 2048 frames), so about
  4000 levels under ``maxrecursion`` (16384 frames; about 680 before the
  visitor was made iterative).  The time of the case lifting of the port
  bounds such a chain first: it is quadratic in the chain, 74 s of the
  118 s of the import of a chain of 2000 levels; a chain of 3500 levels
  imports in 255 s.

Unbounded integers
==================

Curry ``Int`` is unbounded. The existing two-word inline Int node holds
signed 64-bit values. Arithmetic keeps the checked inline fast path and
promotes overflow to a BigInt node. Every result that fits the inline range
is demoted, including the negative endpoint. Comparisons and constraints
therefore have a canonical representation for each value.

A BigInt node owns immutable libtommath storage outside the GC heap. Heap
nodes register a finalizer with either collector; copies of immutable
integer values share their node. Module constants live in the literal
arena for the process lifetime. The runtime privately links the public
domain libtommath 1.3.0 sources from ``extern/libtommath``; generated code
and installed headers do not depend on its headers. Its origin is
https://github.com/libtom/libtommath and its license is in
``extern/libtommath/LICENSE``.

Integer literals beyond the inline range are stored as decimal strings in
ICurry JSON and constructed when the module loads. The compiler and the
ICurry interpreter use the same canonical runtime factory. Python values
use decimal conversion at the boundary to preserve every digit.
