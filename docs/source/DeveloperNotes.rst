===============
Developer Notes
===============

This page holds the facts a developer of Sprite needs and a user does not.

Value conversion
================

Results first use the bindings' native converter for normal-form Ints
(including big integers), Floats, Chars, Bools, lists, tuples and unit.
An explicit stack traverses these values while holding the GIL and runtime
heap gate. Static element types preserve the ``[Char]`` to ``str`` rule,
including empty Strings; without a known element type, only a nonempty list
of Chars becomes a String. Unsupported subterms, including user constructors,
functions, free variables and partial lists, use the Python ``ToPython``
converter. ``ToPython(native=False)`` forces that reference path for parity
tests. Expression-symbol tables are shared within a session and invalidated
when a module is loaded, reloaded or parsed, and at reset.

Logging
========

The logging variables are in :doc:`CommandLineInterface/EnvironmentVariables`.
The package logger is ``curry``; modules use ``logging.getLogger(__name__)``.
Configuration happens once at import. Keep messages at module and toolchain
decision sites, with the module name first and guard expensive diagnostic
work with ``logger.isEnabledFor``. Evaluation steps and graph nodes do not
emit records.

.. _free-threaded-audit:

Free-threaded Python
====================

The bindings opt in with ``pybind11::mod_gil_not_used()`` (pybind11 3.1.0). The supported C++ API permits threads to import modules,
build terms, evaluate and consume separate ``Results`` objects concurrently. The runtime
serializes its process-wide heap: two evaluations still step one at a time
per heap, while Python work outside native metadata/heap operations can run
in parallel on a free-threaded interpreter. Curry evaluations are serialized.

The bindings release the GIL while the runtime steps or waits, take it
for Python callbacks and conversion and poll signals while they wait.  A
deep goal starts on the caller's thread; when an unwind and a retry make
no progress, it continues on a retained worker with a large stack
reservation (the flag ``worker_stack``, 1 GiB by default; ``None``
disables the escalation), and a refused reservation halves down to 64
MiB.  ``stack_limit`` bounds the caller's stack.

The platform probes the caller's stack floor once per thread and caches even
an unavailable result. POSIX cache entries also carry the process ID, so a
forked child probes again. Each runtime entry reads this cache before applying
the existing stack-limit clamp and safety margin; worker reservations keep
their separate accounting.

``PYTHON_GIL`` belongs to the user. Package children inherit its presence or
absence and its value. The 3.14t CI lane runs the unit suites with
``PYTHON_GIL=0`` and the concurrency suite again with the variable absent;
the suite checks the actual GIL state after importing the extension.

The table inventories shared state audited on 2026-10-18 in the Python
API. It excludes the JIT modules added on 2026-10-30. The heap gate is the
lock that serializes access to the process-wide heap. A native metadata
transaction groups C++ operations and registry publication under that gate.
The trap is the first call of a function whose code is not yet materialized.
Deep evaluations can continue on a worker with a larger stack. Python
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
   :widths: 20 30 50

   * - State
     - Location (under ``src/python``)
     - Protection

   * - Singleton and hard reload
     - ``__init__.py; interpreter.__init__``
     - Public functions resolve the interpreter once per call; flags/modules are live read-only views. Hard reload retires/publishes under a native metadata transaction and passes flags explicitly, without changing the environment. Initial imports use Python import serialization.

   * - Session, reset, reload and flags
     - ``interpreter/{__init__,session,flags}.py``
     - Reset and reload native/publication phases share the existing heap gate, with tiered waits outside. Settings are validated privately and published as a new dict. Reload builds privately and updates complete metadata without clearing mandatory slots; it retains module identity. Tokens/versions enforce the stale rule. FLAG_INFO/defaulting tables are immutable after initialization.

   * - Paths and streams
     - ``interpreter/session.py; config.py; toolchain/_system.py``
     - Imports take path snapshots. Literate-source scope and child CURRYPATH are ContextVars; subprocesses get copied environments. The public path list retains its API. Stream references publish by assignment; Python stream objects provide their own I/O synchronization.

   * - Module registry and packages
     - ``interpreter/import_/``
     - Dependencies prepare outside the native metadata phase. A context-local provisional registry supports recursive symbol resolution. Under the heap gate, construction rechecks the session and existing module and publishes a complete canonical module; only the registry/parent update uses the short interpreter lock. Code generation keeps only its bootstrap module private and preserves real dependency imports.

   * - Python import hook
     - ``lib/__init__.py; interpreter/session.py``
     - A short hook-registry lock tracks names/deduplicates hooks. Python owns sys.modules publication. Reset snapshots tracked names and acquires each Python module-name lock before eviction, without holding the heap or a Sprite mutex while waiting.

   * - Anonymous names and expression keepalive
     - ``interpreter/compile.py``
     - A small counter lock allocates process-unique names. Registry removal and keepalive append use the interpreter metadata lock; no native call or evaluation is inside that lock. Reset retires the session under the heap gate.

   * - Backend instances and retired libraries
     - ``backends/__init__.py; backends/cxx/interface.py``
     - Construct backends outside the singleton lock and publish with setdefault. Retirement runs in native session transactions; the retained-library list is append-only under that gate. Backend objects are stateless after construction.

   * - Native object loader
     - ``backends/cxx/loader.py``
     - Dependency imports and background waits precede the native metadata transaction. File identity/stamp is rechecked after imports and at native entry; changed products retry. Registry checks/open/adoption/publication share heap ownership. No Python loader lock spans a native wait.

   * - Tiered state
     - ``backends/cxx/tiered.py``
     - Native metadata transactions serialize these updates with their native operations. Job waits remain outside transactions and poll between bounded waits. Temporary names share the gate. No Python mutex transfers to the large-stack worker.

   * - First-use materialization and bytecode
     - ``backends/cxx/materialize.py``
     - Materialization and pending-registry operations use heap metadata transactions. The trap already owns the heap through compilation/adoption; lazy first-use semantics remain. BYTECODE values are complete before publication and read by a single dictionary lookup; published bytecode is immutable.

   * - Product locks
     - ``toolchain/_productlock.py``
     - Per-path RLock ownership plus flock; recursion is thread-local. Registry entries are reference-counted while in use. Fork callbacks close inherited descriptors and reset locks; unwinding an inherited context does not release a parent lock. Existing unwritable/no-flock fallback retains thread exclusion and atomic publication.

   * - Generated source and objects
     - ``toolchain/_makecurry.py; backends/{generic,cxx}/toolchain.py; materialize.py``
     - Import/render/link-command preparation happens before the file lock. Sources, objects and stamps publish through unique temporary names and rename. A contender accepts a current product another producer published. Plans advance their own pipeline instead of reselecting stale later products between stages. A reader rechecks identity/stamp after importing dependencies.

   * - Product cache and pruning
     - ``toolchain/_productcache.py``
     - Entries are immutable, first-producer-wins directories published by rename. A thread/process lock beside the cache root covers store/restore/prune; restore pins the entry for placement. A separate counter lock protects updates/resets. Forced rebuilds still replace local products, retaining a published cache entry of the same content key.

   * - Creation permissions
     - ``cache.py; toolchain/_productcache.py``
     - Exclusive temporary-file creation with mode 0666 and directory creation with mode 0777 obey the real umask without changing it. Native products and PCH files use unique temporary names.

   * - SQLite and source memo
     - ``cache.py``
     - Thread-local connections and a reset generation; in-progress transaction slots retain their connection. Slots are local to their creating toolchain transaction/thread. A memo RLock protects pure memo construction and counters. SourceInfo objects are read-only snapshots.

   * - Configuration lazy values
     - ``config.py``
     - A configuration RLock covers initialization and path reset; currypath returns a copied list. Published scalars are immutable. No native heap entry occurs under the config lock.

   * - Signature tables and interfaces
     - ``typecheck/sigtable.py; exprtype.py``
     - Interface-cache/decode locks and a per-table RLock protect publication. Resolve module names and native symbol tags before taking the table lock. Weak callbacks remove matching entries under the same lock. Returned instance maps are snapshots; schemes/decoded declarations/synonyms are read-only after publication.

   * - Type records and symbol maps
     - ``typecheck/builder.py; terms.py``
     - Resolve native node identity outside the record lock; protect record updates/weak callbacks. Interpreter publication creates one record. Symbol maps build from one registry snapshot and publish a complete tuple/map. Type-variable ids use a counter lock; inference/unification cells are private to each problem.

   * - Module wrappers and constructor classes
     - ``objects/terms.py; classes.py``
     - ModuleInfo cache locks cover Python-only wrapper construction. Classes/fields finish before module publication and are immutable for that version. Reload prepares complete replacements and updates owner references before publication. Raw-symbol selection remains a ContextVar.

   * - Shared free variables and iterator payloads
     - ``expressions.py; typecheck/builder.py; objects/terms.py``
     - Shared node/owner publish as one tuple; node check/create and external-freevar counters use native metadata transactions. A marker lock commits compatible inferred types with pure unification. Cursor weak-registry updates/callbacks have their own lock. IteratorSource buffers/cursor consumption run in serialized C++ Python-generator callbacks under the heap gate; conversion state belongs to one evaluation.

   * - Results and Stream
     - ``objects/results.py; interpreter/eval.py``
     - A short per-iterator lock claims a busy flag, released before stepping/callbacks; overlapping use keeps Python generators' existing ValueError behavior. Cleanup runs under that claim. Deferred results/streams check their creation session before starting and on both sides of each native step. Separate results can be consumed concurrently.

   * - Evaluation statistics
     - ``backends/generic/eval/evaluator.py; interpreter/stats.py``
     - A totals lock covers Python counters/weak registry and its version. Native counter reads happen outside the lock; version changes retry the snapshot. Direct single_step accounting remains supported. Returned stats are private snapshots, not a global pause of all activity.

   * - Compilation time, warnings and parser caches
     - ``toolchain/_makecurry.py; _curry2icurry.py; flat2icurry/interfaces.py; backends/cxx/toolchain.py``
     - Thread-local compile nesting/start with locked accumulation. Short locks cover rewrite statistics/warnings and compiler warning sets. FlatCurry caches publish complete read-only trees with setdefault; finder instances are private. PCH files publish atomically with unique names; digest lru_caches use standard-library synchronization.

   * - Temporary directories and dispatch/type factories
     - ``toolchain/_str2module.py; utility/{visitation,proptree}.py``
     - Directory snapshots and updates share a short lock. Dynamic class factories have registry locks. Dispatch ordering computes from a handler snapshot outside its lock and publishes an immutable tuple only if the registered types still match; handlers run after releasing locks.

   * - Binding trap hook
     - ``backends/cxx/curryrtbindings/module.cpp``
     - set_trap_hook already uses heap_access; invocation already runs under the locked rewrite step. Retain a local callable reference across reentrant replacement. Its process-lifetime storage intentionally avoids Python teardown destruction; this is not a subinterpreter opt-in.

   * - Binding literals, constants and graph lifetime
     - ``backends/cxx/curryrtbindings/{icurry,graph,dynload,tiered}.cpp; heap.hpp``
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
thread-owned product locks, a forced producer under a reader and a trapped
first use while another producer prepares native imports. Existing
``unit_evaluation_lock.py`` and ``unit_issue153.py`` cover reentrant callbacks
and the worker handoff.

Windows object publication
--------------------------

A load maps the canonical object directly, in a read-only installation as
well. Under the product lock, Windows first tries to replace the canonical
DLL directly. On access-denied or sharing-violation errors it renames the
existing DLL to ``<Module>.dll.old-<pid>-<counter>`` before replacing the
canonical name. The next publication collects generations owned by exited
processes and keeps those of live processes. An owner that cannot be opened
(for example, access denied) conservatively counts as alive. A load creates
no file. The regression switch ``SPRITE_TEST_WINDOWS_PUBLICATION=1`` forces
the retirement protocol, including on POSIX; it does not change loading.
Readers retry a failed open when the product snapshot changed, with at most
three attempts. Tiered publication tries the product lock without blocking;
a busy lock leaves the private object in use and the publication to the
holder of the lock.
A tiered reload on POSIX uses a distinct spelling of the canonical path,
so that ``dlopen`` opens the new file instead of returning the old mapping;
it creates no link and no copy. Windows normalizes that spelling, so a
second adoption under an already mapped canonical name declines with a
logged reason and the edited module stays interpreted until the next process.
The tests cover mapped readers, collection of live and dead generations and
read-only products. Neither a generation nor an old private ``.tiered`` copy
may appear in a staged library or a wheel.

The failure test of rule N
==========================

The failure half of the whole-cell read of N is implemented: ``RuntimeState::procN`` tests the tags of all direct successors
of a constructor cell before the scan descends, including
when a step returns a constructor at the cursor.  The existing
``inspect::fwd_chain_target`` dereferences transparent forwarding chains:
each successor denotes the shared cell at the end of its chain, as in the
whole-cell entry test.  A failure tag returns
``T_FAIL``, recording the failure for an enclosing capsule; ``procD_loop``
drops the configuration without overwriting a shared cell.  Each constructor
visit costs one pass over its direct successors and their forward chains,
with no recursion, allocation, descent into constructors or evaluation of
guards or functions.  Choices are still pull-tabbed only at the scan cursor
(N.2) and the one-step rule is unchanged.  Compiled functions and the ICurry
interpreter (``icurry_step``) share this normalization loop.  ``CursorFail``
tests this failure half and exhausts with no value on both routes.  The
constraint half of the whole-cell read is not implemented.  Its regression program ``CursorBeta`` asserts exactly
``Pair True True`` and termination on both routes, as expected failures:
it yields that answer without exhausting because its second field is a live
``_StrictConstraint`` (``T_CONSTR``) behind a forward chain, which only the
cursor lifts.  Processing it before descent would require position
bookkeeping, a constructor spine copy and a constraint lift in ``procN``;
that rule is not implemented here.

The checker mode
================

The interpreter flag ``checker`` (off by default) checks runtime
invariants of the Fair Scheme. It preserves the program's steps, values
and counters, but costs time and memory: flagged cells stay alive for the
life of an evaluation. Every hook tests whether the checker is enabled.

A violation raises ``curry.backends.cxx.curryrtbindings.InvariantViolation``,
an ``AssertionError`` whose message names the invariant, event,
configuration, identifiers and goal position. Under ``sprite-exec``,
``SPRITE_DEBUG=1`` exposes the full report::

    SPRITE_DEBUG=1 SPRITE_INTERPRETER_FLAGS=checker:true sprite-exec Peano.curry

The checker tests these properties:

* At a fork, each decided identifier agrees with the root of its group.
* A fork preserves its parent's decisions and records its own choice.
* At a yield, the value has no reachable choice, function, failure,
  constraint or bound variable outside excluded generator and function
  argument subgraphs.
* Variable groups have one root binding and no cyclic generator instance.
* Merging two bound groups guards the discarded binding with strict equality.
* Dispatch and failure drops leave shared cells unchanged.
* Equality narrows a free variable against a constructor; two free
  variables produce a constraint.
* Escapes split queues consistently and involve argument-derived choices.
* A pull-tab copies its spine and preserves the choice identifier.
* Each variable has one generator, with its identifier at the root.
* Instantiation and private spine copies preserve the values seen by
  every compatible configuration.
* Cells created at a flagged redex inherit its argument-derived flags.
* A demand for head normal form follows a case in the function's
  definitional tree and a failure comes from a permitted leaf.

Comparisons and flag propagation have bounded walks. An event over its
budget is counted and the affected checks are suppressed. Constraint
lifts, schedule replay and private copies of set-function capsules are
not checked. Built-in functions have no definitional tree and are not
checked for the last property.

For definitional-tree checks, use ``checker:true,interpret:all``. A tree
reconstructed from bytecode stays available when the C++ backend of the
JIT later swaps that function to compiled code. Functions first called
after that swap have no bytecode and cannot acquire a tree. LLVM swaps
retain bytecode and its tree. Objects loaded ahead of time have no tree;
the other invariants still apply.

On an empty capsule queue, deferred failure is reported exactly when the
capsule produced no value and recorded an outside failure, regardless of
inside failures. Otherwise the set stands, possibly empty. The checker
records inside failures for diagnostics.

``src/curryrt/checker.hpp`` and ``checker.cpp`` document the hooks.
``tests/unit_cxx_checker.py`` runs known-good programs under the checker,
compiled and interpreted and provokes one violation per check through
``curryrtbindings.checker_debug_*``.
``curryrtbindings.checker_counts`` reports the event counts.

The depth bounds of the toolchain
=================================

The Curry-to-ICurry translation and the expression walks of the import
use explicit stacks. A literal list of 10800 elements imports and runs
under ``interpret:new`` (``tests/unit_curry2icurry.py``,
``TestDeepExpressions``). Two bounds remain:

* The small JSON codec used for summaries recurses in C. Above about
  12000 nesting levels it can overflow the C stack (``RecursionError``).
  The ``utility.maxrecursion`` context manager raises the Python recursion
  limit to 16384; it does not raise this C-stack bound.
* Case lifting is quadratic in a chain of nested if-then-else expressions.
  The monadic analysis also follows the resulting chain recursively.

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
image constants and constructed when the module loads. The compiler and the
ICurry interpreter use the same canonical runtime factory. Python values
use decimal conversion at the boundary to preserve every digit.

Constraint classes
==================

The union-find parent table is sparse: an absent identifier denotes a
singleton, and unions create entries for their roots. Weighted union and
path halving retain the previous representative rules, including the
historical doubling of a root's weight on a repeated equality. That weight
affects later root choices and must not be replaced by class cardinality.
A fork shares its constraint store until the first write,
which copies only the participating identifiers and preserves spare capacity
in the endpoint log. Storage no longer follows the process-wide identifier
counter. The log contains the endpoints of real unions in insertion order;
every member of a non-singleton class occurs in it, so the collector and
invariant checker still visit all retained free variables.

The module image
================

Format 5 (2026-11-01)
---------------------

A module image, ``M.img``, lives beside ``M.icy``. The translator writes it
atomically after merging runtime built-ins and running the six optimizer
passes. ICurry text and its compatibility translation remain unchanged;
No module JSON product is written or read. Tools recover bodies from ICurry
text; inline-body and unfolding summaries still use the small JSON codec.

The format is independent of pointer size and native byte order. Integers
are little-endian; strings are UTF-8 with a 32-bit byte count. The prefix
contains an eight-byte magic, a 32-bit format version and the length of a
header. The header records the ICurry-text SHA-256, route version, inline
budget, and each direct import's image SHA-256. The header also records
sorted registered primitive names. No field records a machine path.
Sections contain imports and aliases, ordered data types and constructors,
function declarations, bytecode and constants and translation metadata.
Strings are length-delimited and record arrays begin with a 32-bit count.
Unknown versions, truncation and invalid section lengths are rejected.

Function bytecode uses the interpreter's existing 32-bit code units and
frame sizes. Constants have explicit tags: symbol, constructor data type,
integer (decimal text, including large integers), character (code point),
float (IEEE binary64), string, argument-free partial application or literal
case value set. Symbol and type references carry qualified names, never
addresses. The native reader creates all local tables before resolving
constants against those tables and imported runtime modules. Built-ins use
the runtime's existing tables. Attachment uses ``icurry_attach``; the JIT
continues to obtain code and bound constants through ``icurry_bytecode``.

The native reader also has a read-only summary mode. It reuses the loaded
symbol tables and skips code and constants, without attaching or allocating
literal nodes. Translation uses that mode for the complete import closure,
even when the imports run from ahead-of-time objects and temporarily supplies those
summary records to the existing passes. Each pass runs once before emission.

The last section is an array of function metadata records, in declaration
order. It retains the optimizer's inline-body, alias, unfolding and
monadic metadata. Importer translation reads this section, without decoding
JSON or reconstructing executable ICurry bodies. Python receives symbol
records with names, arities, visibility, flags and constructor order. The
``.fint`` remains the typed boundary's input; ``.icurry`` remains the source
of record fields and synonyms.

Currency is determined by content: source, route, budget and imported image
digests must agree. Sorted registered primitive names must also agree. A malformed or old image is diagnosed and regenerated
through translation. A current compiled object takes precedence over a
current image under ``interpret:new`` and ``interpret:off``; sibling product
modification times do not decide that precedence. ``interpret:all`` uses
images. Modules compiled from text use the same writer and native reader.

Type flags include ``F_DICTIONARY`` for names beginning with ``_Dict#``.
The runtime tests this bit when head-normalizing a class selector. Generated
C++ tables carry the same bit (generated-code format 21); data type flags
use 16 bits, as info table flags do.
Binding compiled code to a type kept across a reset preserves all these bits.

The eight-byte magic is ``SPRTIMG`` followed by a zero byte. The header is
ASCII JSON, with its length in the prefix; its ``body`` field is the SHA-256
of everything after the header. The native reader compares the header with
the header the plan validated before creating tables, rejecting a replacement
between validation and attachment. The body order is: module name, imports, aliases,
module metadata, types and constructors, function declarations, one bytecode
record per function, then function translation summaries. Metadata entries
are key strings followed by a 32-bit kind (0 string, 1 signed 32-bit integer,
2 boolean) and a value. Constant tags are 32-bit character codes: ``R``
(symbol), ``T`` (the type of a named constructor), ``I``, ``C``, ``F``,
``S``, ``P`` and ``V``. Built-in function bytecode records are empty. Small
literals use the runtime tables; larger literals are interned across the
functions of the image. Parent and child module names are bound separately.

The symbol layer currently uses the same lightweight ``IModule.fromBOM``
declarations as compiled objects; it does not reconstruct executable ICurry
bodies. Every library module has an executable image. An external without
a primitive compiles to a step that raises ``not implemented``; an external
type has no constructors.

Generated C++ carries an ``INPUT`` record (source SHA-256, route, inline
budget and sorted registered primitive names). The ABI stamp retains it in
its import-provenance JSON. Both records are checked before pipeline-order
selection, so translating a new image cannot make an old object current.
A newer sibling image timestamp does not invalidate an otherwise current
object. Explicitly saved objects outside the product tree continue to load
explicitly.

Image loading registers a shutdown barrier for the LLVM hot tier: it turns
off new hot work and waits for any native compilation to leave the LLVM
context before Python destroys that context. This matters when image
loading makes short processes exit while a compile is still in flight.

The image digest keys the compiled product cache and imported-body
provenance. No module JSON or parsed-module cache remains. Read-only
product directories and text modules use process-private images. A foreign
inline budget also uses a private image. Inspection and saved C++ read the
ICurry text and optimize it against image summaries.

Persistent LLVM objects
=======================

The LLVM backend writes one ``M.jit`` beside ``M.img``. Its envelope starts
with the eight ASCII bytes ``SPRTJIT4`` and a little-endian uint32 index
length, followed by a compact ASCII JSON index and a list of independently
zlib-compressed objects from ``TargetMachine.emit_object``. Older format
envelopes are cache misses. The index holds the cache key and each object's
compressed size, SHA-256 digest of the compressed bytes and one record of
function name, exported step symbol and constant-slot indices. The header
also records the envelope's size and modification time: an even whole second
expressed in nanoseconds, which survives installation copies and FAT32's
two-second resolution. A copy that does not preserve this time misses at
attachment; a later publication merges same-key objects only after verifying
their digests. An attached index pins an open POSIX file descriptor, so
replacement by another process does not invalidate unresolved objects. The
descriptor closes explicitly after the last object is read or dropped, or
when its image generation is detached. Resolved entries retain no native
bytes; later publication recovers same-key objects from the envelope on disk. The envelope carries no addresses or paths.

Each bytecode constant used by a function is an external LLVM symbol, named
by a short module-local function ordinal and the slot index. The index maps
qualified function names to these exported step symbols. On first use the
loader reads the slots of the current image's bytecode and supplies their
addresses with ``JITLibraryBuilder.import_symbol``. Runtime symbols resolve
from the process. ORC links the object with ``add_object_img``; Unix uses
JITLink to preserve unwind registration across independent objects. Resource
trackers keep the code alive. Each object contains exactly one function, so
resolving one step cannot materialize unrelated functions.

Attachment reads only the index and checks its key, file size and mtime. It
retains decoded entries directly, creating object views only on use. It
installs ``icurry_cached_step`` for cached functions. On first use this
runtime step calls a Python hook with the info-table address; the hook
serializes with the hot tier, reads and verifies that object's digest,
decompresses its bytes, registers it with ORC and resolves its exported
step. Like ``trap_step``, the resolving step installs the address on the
evaluation thread and runs it on the same redex. A failure logs once and
restores ``icurry_step``. The hot tier uses the same resolver for cached
functions and posts swaps at scheduler safepoints; it emits no replacement
object on a cache hit. ``jit:eager`` resolves the full cached module at
load; ``jit:off`` reads nothing. Index registration does not count as a
swapped function.

The content key includes the image header's body digest and module name, the
runtime ABI digest used by generated objects, the helper bitcode digest, the
emitter digest, the image format version, llvmlite and LLVM versions, CPU
name and target triple. A changed key or corrupt envelope is a miss. No
installation path enters the key. Each later hot batch appends one object
per function, and links only those objects. The stage fill uses the same
per-function emission. Uncached functions share optimizer batches of at most
32 steps. The hot and eager callers release the JIT lock between batches and
take it again for one publication per module, allowing waiting cached calls
to resolve. Each optimized clone retains one step and its reachable helper
code for object emission. The hot worker prioritizes larger bytecode bodies
and posts each emitted step immediately while the remaining objects are
generated. Shutdown cancels unlinked hot work between LLVM phases and optimizer
batches, and waits for the whole group to publish its completed objects. Cached functions are never
re-optimized. Reattachment reuses linked addresses by key; resource trackers
keep each generation alive.

Publication holds the existing product lock and replaces a temporary file
atomically, so concurrent readers see a whole generation. A writer preserves
an existing current superset. Concurrent differing batches may replace one
another; each remains valid. If the product directory cannot be written,
``SPRITE_JIT_CACHE/<Full.Name>/<key>.jit`` is tried. Without either writable
location nothing is persisted. This is a local executable-code cache with the same
trust requirements as generated shared objects, with one generation per module.
A local stage fills the library cache; ``SPRITE_STAGE_JIT_CACHE=0`` skips
the fill with one notice. CI enables it in one default C++ shard only.
Wheel builds and Windows skip it.

The local slot is beside the image actually attached. A private image
uses its private directory, including for a foreign inline budget. A writer
checks that the slot's image is still the attached image before replacing
an entry with a different key. A writable private image directory takes
precedence over the per-user fallback.

The backend interface
=====================

An :class:`IBackend <curry.backends.IBackend>` mediates interactions between
an interpreter and a backend.  A backend has one instance, which every
interpreter that targets it shares; the object is stateless and the state
of an interpreter lives in an interpreter state the backend attaches to
it.  The backend is ``curry.backends.cxx``, the implementation of ``backend:cxx``; it implements
the interface in its module ``interface``.

A backend implements the target-specific aspects of compilation and evaluation.
The interface includes the following:

  * **Compilation**

      - ``compile``:
        Translates ICurry to generated C++.

      - ``materialize``:
        Materializes the functions of a module as runnable code.

      - ``write_module``, ``load_module``, ``object_file_extension``:
        The C++ source the backend writes for a module, which
        :func:`curry.save` compiles into the shared object that
        :func:`curry.load` reads.

      - ``extend_plan_skeleton``:
        The steps the backend adds to the compilation pipeline of
        :ref:`sprite-make <sprite-make>`.

      - ``module_loaded``:
        The hook of a load. With LLVM it compiles queued eager functions
        or starts the hot tier. With the C++ compiler backend it arms the
        whole-module compile; eager compilation waits here for the object.

  * **Evaluation**

      - ``make_node``:
        Creates one node of a Curry expression graph.

      - ``create_evaluation_rts``:
        Creates the runtime state of one evaluation.

      - ``before_evaluation``, ``after_evaluation``:
        The hooks around an evaluation.  The runtime applies the
        objects that finished compiling in the background.

      - ``lookup_builtin_module``, ``fundamental_symbols``:
        The implementations of the external declarations of the built-in
        Curry modules and the symbols every backend provides.

  * **Statistics and inspection**

      - ``num_collections``, ``gc_seconds``, ``gc_counters``,
        ``tiered_counts``, ``scheduler_counters_enabled``:
        What :func:`curry.stats` reports.  A backend without a collector
        of its own answers zeros.

      - ``getimpl``:
        The generated code of a symbol, for :func:`curry.inspect.getimpl`.

  * **Runtime State**

    Data associated with the evaluation of a Curry expression.  Each call to
    :func:`curry.interpreter.Interpreter.eval` gives rise to a new, unique
    runtime state.  This way, any number of evaluations can occur
    concurrently without interfering with one another.

    This captures the relevant state of the interpreter that
    requested evaluation (such as its interpreter flags) and houses the
    necessary data structures, such as the work queue of the Fair Scheme.

  * **Interpreter State**

    The backend attaches a state object to each interpreter to track
    backend-specific information, such as the identifiers of choices and
    free variables, so that no two expressions created by the same
    interpreter share one.  :func:`curry.reset` installs a new state.

The scheduler design is the Fair Scheme.  A queue holds the
configurations, each an alternative of the computation with its
fingerprint of the choices it made.  A step rewrites one redex; a choice
at the root forks the configuration; a free variable at a constructor case narrows to the matching
constructors; at a literal case it suspends.  The runtime runs the scheduler in its library
``libcurryrt`` (``src/curryrt``), with compiled step functions or the bytecode
of its ICurry interpreter.

Compiler flags of the runtime
=============================

The runtime library, the bindings, the generated code and the C++ tests
compile with ``-fno-strict-aliasing``: the node graph is read through the
pointer union ``NodeU``, which the aliasing rules of C++ do not describe.
``CXXFLAGS`` in the environment adds to the flags of the generated code
and cannot remove it.

.. _developer-run-statistics:

Run statistics
==============

The fields of the collector are on every line of ``sprite-exec --stats``
and in :func:`curry.stats`; a runtime built with ``COUNTERS=1`` appends
the scheduler counters.

``gc_roots_seconds``, ``gc_trace_seconds``, ``gc_sweep_seconds``, ``gc_registries_seconds``
    Seconds the collections of the node collector spent in each phase: the
    roots (the configurations of the queues and the nodes Python holds),
    the trace from the roots, the block sweep and the registries (the
    free-variable tables, the generator nodes, the queues and the sets).
    The sum is below ``gc_seconds`` by the small fixed costs of a
    collection and, in the stress mode, by the verifier.

``gc_marked``, ``gc_marked_old``, ``gc_marked_young``
    The nodes the collections marked: all of them, those that the collection
    before had marked as well (old) and those allocated since (young).  The
    old nodes are the live nodes a generational collector would not trace
    in a minor collection.

``gc_configurations_pushed``
    The configurations whose roots the collections pushed.

``gc_queues_destroyed``, ``gc_configurations_destroyed``
    The queues of set functions that no root reached, destroyed by the
    collections and the configurations destroyed with them.  A
    configuration that a fork or a drop freed is not counted.

``gc_old_redexes``, ``gc_old_slot_writes``, ``gc_old_nodes_written``, ``gc_old_blocks``
    The writes into old nodes between the collections, summed over the
    intervals: the writes of a step into a redex that was old, the other
    pointer writes into an old node (a forward chain shortened in a slot,
    the generator of a free variable, the binding of a variable, the
    string advance of ``writeFile``), the distinct old nodes written (a
    loop that rewrites one old redex at every step counts one node and
    many writes) and the blocks with such a write.  They are the input of
    a write barrier that does not exist yet.  Only a runtime built with
    them (``make GC_WRITE_COUNTERS=1``; they cost a tenth of the
    instructions of a deterministic program) counts them; the default
    build reports 0.  The setting changes the
    runtime headers that generated code includes, so a module is compiled
    with the setting of the installed runtime and compiled again when it
    changes (the ABI stamp). Use ``make GC_WRITE_COUNTERS=1 stage`` to
    enable it and ``make GC_WRITE_COUNTERS=0 stage`` to disable it.
    ``SPRITE_GC_REPORT=1`` prints the counters of every collection (see
    :doc:`CommandLineInterface/EnvironmentVariables`).

Seconds are printed with six decimals.  The same numbers are available in
Python from :func:`curry.stats`, which returns a dict with these keys in this
order; ``str`` of it gives the line above.

Scheduler counters
------------------

A C++ runtime built with ``make COUNTERS=1`` counts what the scheduler does
with its queue of configurations.  The flag changes the runtime library and
its Python bindings only; a plain build has none of the code and the
generated modules of a plain build serve an instrumented one.  Use ``make COUNTERS=1 stage`` to enable it and
``make COUNTERS=0 stage`` to disable it.  The
instrumented runtime costs about one to three percent more instructions and
a word more per node.

With the counters, ``--stats`` appends these fields after
``gc_old_blocks``, and
:func:`curry.stats` adds the same keys:

``serial_steps``
    Steps taken while the outermost queue held one configuration.  The
    serial fraction, ``serial_steps`` over ``steps``, bounds the gain of a
    thread pool over the queue.

``nested_steps``
    Steps taken inside a set function, whose alternatives run in a queue of
    their own.

``shared_steps``
    Steps whose redex another configuration created.  Every node carries the
    serial number of the configuration whose step allocated it; a redex made
    by an ancestor before a fork, or by a sibling, is work that more than one
    configuration reaches.  The shared-work ratio, ``shared_steps`` over
    ``steps``, bounds the work a design with one copy of the graph per
    alternative would duplicate.  A node built outside the scheduler, such as
    the goal, has no creator and never counts.

``queue_max``
    The largest number of configurations in the outermost queue.

``configurations``, ``failures``, ``failed_steps``
    The configurations of the outermost queue: those that ended with a
    value, a failure or a fork and those still in the queue when the
    statistics were read.  ``failures`` and ``failed_steps`` are the ones
    that failed and the steps they took.

``lifetime_median``, ``lifetime_mean``, ``lifetime_max``
    The steps a configuration of the outermost queue took from its creation
    to its end by a value, a failure or a fork.  The steps of the set
    functions it evaluated count for it.  The median is exact below 1024
    steps; above, it is the lower bound of the power-of-two bucket that
    holds it.

``nested_configurations``, ``nested_lifetime_median``, ``nested_lifetime_mean``, ``nested_lifetime_max``
    The same for the configurations of the queues of set functions.

The counters are per evaluation and summed over the evaluations of the
interpreter, like ``steps``; the maxima take the largest value.  The
benchmark harness keeps the fields of every run and tabulates them with
``run_benchmarks counters FILE`` (see ``tests/README``).

Primitives
==========

The runtime resolves a primitive by its qualified Curry name. Register it
before the module's images or compiled objects load.
The image writer and C++ emitter ask ``Module::get_builtin_symbol`` for the same table;
compiled code and images do not encode the implementation language.
Sorted registry names are part of generated input records, product facts
and image headers. A registry change makes these products stale.
Loaders reject missing primitives by name.
The emitter records local shape descriptors, which the loader binds by name;
it does not require a primitive to export a mangled C++ data symbol.
Unregistered externals continue to raise ``not implemented`` when called.
``curry.inspect.getimpl`` identifies registered C++ and Python primitives.

A C++ primitive registers an ``InfoTable`` with
``Module::register_primitive("Module.function", &table)`` during static
initialization. The table and its strings must live for the process. Its step
receives ``RuntimeState *`` and ``Configuration *``. Monadic tables carry
``F_MONADIC``; perform the effect in the step and forward the redex to
``io(value)``. Pure steps forward to the value. IO errors carry an IOError
node and ``ErrorKind::io`` through ``Configuration::set_error``. See
``currylib/library.cpp`` for complete examples. Mutable references use
``Variable::set_successor`` for writes.

Python implementations register through the backend bindings::

  from curry.backends.cxx import curryrtbindings as curryrt
  curryrt.register_primitive('Example.next', 1, lambda x: x + 1, monadic=False)

Registration takes the qualified name, Curry arity, callable and monadic flag.
Names must be qualified and arities must be between zero and 255.
Register new names before the module import. A matching Python registration
replaces the callable in the same table, including while loaded or after reset
with module handles alive. A different arity or flag is an error.
The registration call holds the runtime heap gate until it returns.
Invocation normalizes every argument before it acquires the GIL.
Conversion reads the declared type from the evaluating interpreter's signature
table and module interface, including for private interpreters.
An empty String becomes Python ``''``; an empty list becomes ``[]``.
Results must match the declared type. ``None`` returns unit.
Supported values are integers, floats, characters, Booleans, strings, lists
and pairs. Callables and tables stay alive for the process.
A callable must not block on a lock held by a thread that waits for the heap.
An Int argument or result beyond Python's integer string limit raises an
evaluation error that names the primitive.
Ordinary Python exceptions become Curry IO errors for monadic primitives and
evaluation errors for pure primitives; KeyboardInterrupt and SystemExit pass
through. A monadic effect runs only when its action is evaluated.

Use standard C++ where a portable standard exists: filesystem, clocks,
``std::system`` and heap-side cells. Use Python only where no such standard
exists, including process arguments, hostname, and future sockets and command
pipes. A future C++ implementation can register the same name without changing
Curry code or the image format. ``System.Environment`` is the first Python
registration user; the installation prefix is supplied from Python at runtime
so relocated installations report their actual prefix.

An IORef is one cell shared by the alternatives of a pull-tab.
Reads snapshot its current pointer. ``getElapsedTime`` counts from the library
load. ``setEnv`` changes the native environment, but does not update Python's
``os.environ``. An environment write error names the variable.
``curry.program_arguments`` and ``curry.program_name`` supply the runtime
arguments and module name under sprite-exec and saved programs.
Their Python defaults are ``sys.argv[1:]`` and ``sys.argv[0]``.
Tool options may precede NAME or appear immediately after it.
The first runtime argument, an unknown option, or ``--`` ends tool options.
After NAME, only exact option names and long options with ``=VALUE`` are tool
options; short attached values, abbreviations and combined flags are program
arguments. Only the ``--`` that ends tool options is discarded; a later
``--`` reaches the program. The REPL supplies no program arguments and uses
the loaded module name. Before the first prompt it loads either the
command-line module or ``Prelude``, so the initial name without a
command-line module is ``Prelude``.
