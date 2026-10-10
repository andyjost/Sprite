===============
Developer Notes
===============

This page holds the facts a developer of Sprite needs and a user does not.
The user guide describes one backend, the C++ backend.  The second backend
of the source tree, the Python backend, is a reference implementation behind
a flag until its removal.  This page names the flag, says what the backend
is for, and lists its limits.

.. _reference-backend:

The reference backend
=====================

``curry.backends.py`` is a compiler from ICurry to Python and the Fair
Scheme scheduler in Python.  It was the first backend of Sprite and the
default until the C++ backend took its place (issue #82, 2026-10-06).  It
stays in the tree as a reference implementation until the removal gate
below: the oracle of the values of the C++ backend in the test suite, and a
debugging aid.

The flag
--------

The interpreter flag ``backend`` selects it with the value ``py``.  Every
surface that sets a flag takes the value:

* ``SPRITE_INTERPRETER_FLAGS=backend:py sprite-exec prog.curry``, or
  ``sprite-exec -b py prog.curry`` and ``python -m curry -b py prog.curry``.
  The help of ``-b`` lists no value, and the error for an unknown value
  (``unknown backend 'foo'``) lists none.
* ``:set backend py`` at the prompt of the REPL.  The listing of ``:set``
  shows the backend of the session, and the error for an unknown value
  (``Invalid backend: 'foo'.``) lists none.
* ``sprite-make --py M.curry`` (``-p``, ``--python``) writes the Python
  module of the saved form.  The help and the manual of ``sprite-make``
  omit the option; ``make stage`` and the test runner use it.
* ``Interpreter(flags={'backend': 'py'})`` and
  ``curry.reload({'backend': 'py'})`` in the Python API.  A new interpreter
  starts from the flags of the environment and takes its argument over
  them (:mod:`curry.interpreter.flags`).
* ``configure --with-default-backend py`` for an installation whose default
  it is.
* ``./run_tests --backend py`` or ``--backend both`` under ``tests/``, and
  ``run-tests.sh py`` in CI.

The name ``backend:py`` stays until the removal.  A second name, one that
says "reference", would add an alias to the flag, to the help texts, to
the REPL, to the test runner, to the CI matrix, to the conda recipe and to
the run scripts of the examples, for the month before the removal.  The
removal deletes every call site either way.

What it is for
--------------

* The oracle of the values of the C++ backend.  The test runner runs every
  file on both backends (``--backend both``), the functional tests compare
  both backends with PAKCS, and the pull-request matrix of CI keeps one
  shard on this backend until a month of green nightly runs (the second half
  of stage 4 of issue #82).
* The generated code of a function as Python source.
  ``curry.inspect.getimpl(f)`` gives the Python step function on this
  backend.  The C++ backend gives the generated C++ of a compiled module, or
  the bytecode listing of an interpreted one.  Example 03 prints it.
* PDB into generated code.  Under the flag ``debug`` the backend writes each
  step function to a source file, so a breakpoint in generated code works.
* The flag ``trace``.  The backend prints each step (``S <<<``, ``S >>>``)
  and the queue of the scheduler::

     SPRITE_INTERPRETER_FLAGS=backend:py,trace:true sprite-exec prog.curry > spritelog

  ``spritelog.vim`` at the root of the repository highlights the output.
  The C++ backend accepts the flag and prints nothing; its trace is a build
  of the runtime with ``SPRITE_TRACE_ENABLED``.
* The profiler.  ``sprite-exec -p`` (``--profile``, with ``--psort`` for the
  sort key) runs the program under ``cProfile``.  The rewrite steps are
  Python functions on this backend alone, so the profile shows the program
  there; on the C++ backend it shows the driver, and ``--stats`` reports
  the counters::

     sprite-exec -b py Peano.curry --profile --psort=calls

* The saved form.  ``curry.save(M, 'M.py', goal='main')`` writes a Python
  program that holds the generated code of the module and evaluates the
  goal; ``curry.save(M, 'M.py', module_main=False)`` writes the module
  alone, and ``curry.load('M.py')`` reads it back.  A saved program runs
  under the Python of the installation and reads ``-g NAME`` and ``--help``
  as ``sprite-exec`` does; a goal without a signature is defaulted at run
  time from the type the file records.  ``sprite-make --py M.curry -o M.py
  -g main`` writes the same form (the option is hidden in the help), with
  the bytecode cache of the file beside it under ``__pycache__``, so that
  CPython compiles a generated module once per change.  Example 04 runs the round trip.  On the C++
  backend ``curry.save`` writes C++ source whose entry point is a stub, and
  ``curry.load`` reads the shared object that ``sprite-make --so`` writes;
  the C++ form of ``curry.save`` is an open decision of stage 5 of issue
  #82.  ``tests/unit_loadsave.py`` pins both routes.
* The stepper of the test library.  ``cytest.step`` takes a bounded number
  of rewrite steps of an expression through the step limit of the generic
  evaluator (``Evaluator.set_global_step_limit``).  Both backends provide
  the limit: the Python ``RuntimeState`` counts in its ``StepCounter``, and
  the C++ scheduler stops after the step that reaches
  ``RuntimeState::step_limit`` (``cyrt/state/rts.hpp``), which the adapter
  ``cyrtbindings.StepCounter`` presents as ``rts.stepcounter``.  The graph
  then holds the result of exactly that many steps on either backend, so
  the two tests that use it, ``test_interp_step`` of ``unit_py_runtime.py``
  and ``test_apply_nf`` of ``unit_prelude.py``, run on both;
  ``unit_cxx_steplimit.py`` pins the limit.  ``evaluator.single_step``
  takes one step at the root on both backends.
* The white-box tests of its evaluator: the ``unit_py_*`` files that drive
  the graph classes and the ``RuntimeState`` of the backend directly skip on
  the C++ backend.

Its limits
----------

* It suits small programs.  The C++ backend is more than a hundred times
  faster on the benchmark programs.  In the baseline record of 2026-10-03
  (:doc:`Performance`), 11 of the 30 programs of the dissertation timed out
  at 120 s on this backend and two failed (``Reverse`` and
  ``ReverseUser``); the record holds one repetition of this backend beside
  five of the C++ backend.
* The flag ``recursion_limit`` (default 262144) bounds the Python frames of
  one value: the recursion limit of the interpreter while the value is
  computed.  The backend nests about eight frames per element of a list
  under a function that is not tail recursive, such as ``length`` or
  ``sort``, so the default covers a list of about thirty thousand elements.
  An alternative that reaches the limit runs again after the others and is
  dropped when it overflows again without progress; its ``RecursionError``
  is reported after the other alternatives have run.  A larger limit costs
  about 4 KB of memory per nested element; ``None`` leaves the limit of the
  interpreter as it is.  Issue #62 records the failures of the list
  functions over about a thousand elements under an earlier limit.
* The flag ``step_budget`` (default 2048) is the number of rewrite steps one
  alternative gets before the queue rotates.  Rotation occurs only when
  another alternative waits, in the same queue or in an enclosing one, so a
  diverging alternative cannot starve the others, also not from inside a
  set function.  ``None`` turns the rotation by steps off; rotation on
  residuation and on a Python stack overflow still occurs.  The backend
  ignores the flags ``rotation``, ``stack_limit`` and ``interpret``, and
  the variables of the collector (``SPRITE_GC_*``).
* It has no collector of its own.  ``curry.stats`` reports 0 for
  ``collections``, ``gc_seconds``, ``swapped``, ``failed_compiles`` and the
  ``gc_`` keys.
* ``show`` of an ``Int`` bound by ``=:=`` under ``$##`` does not finish
  (issue #60); the C++ backend prints the value.
* The backend asserts on a set guard of an enclosing set at the root of a
  configuration, one known failure of the set-function corpus
  (``unit_cxx_scheduler.py``, ``unit_setfunctions_bugs.py``,
  ``unit_setfunctions_semantics.py``); the C++ backend passes it.
* The queues of a set function hold references to their configurations.
  After the escape of a choice the two queues of the split share them, and
  a step in one queue takes effect in the other; the C++ runtime clones a
  shared configuration before a queue steps it.  The clone of a capsule
  for an alternative that bound a variable of its goal after the start
  (issue #86) copies the configurations instead.  On both backends the
  clone goes into a private copy of the spine of the reference that read
  the binding, so a second reference of the same alternative to the
  capsule clones it again; a binding the alternative holds at the start
  of the capsule is absorbed then, with no clone.
* A string built by :func:`curry.expr` is one ``_biString`` node, which
  prints as ``_biString 'hello'`` until its first step unfolds it; on the
  C++ backend it is the list of its characters.  The ``repr`` of a negative
  ``Float`` node differs between the backends.

The checker mode
----------------

The interpreter flag ``checker`` (off by default) turns on the checker of
the run-time invariants of the Fair Scheme, the checker mode of section 6.5
of the memo on the Fair Scheme proofs.  Both backends have one.  The
runtime state of the reference backend holds one ``Checker``
(``curry.backends.py.eval.checker``) while the flag is on, and ``None``
otherwise; the runtime state of the C++ backend holds one ``Checker`` of
``src/cyrt/checker.hpp`` (``RuntimeState::checker``, a pointer that is null
otherwise).  Every hook in a runtime is one test of that attribute or
pointer, so the flag-off path costs one test per event and makes the same
steps, values and counters as before, and the checker changes no step, no
value and no counter when it is on; it costs time, and memory, since it
keeps every flagged cell alive for the life of the runtime state.  A
violation raises ``InvariantViolation``, an ``AssertionError`` whose
message names the invariant, the event, the configuration (its queue, its
set, its fingerprint, its groups, its root), the identifiers and the goal
position; on the C++ backend the class is
``curry.backends.cxx.cyrtbindings.InvariantViolation``, raised from the
hook through the scheduler as the step limit is.  To run a program under
the checker::

   SPRITE_DEBUG=1 SPRITE_INTERPRETER_FLAGS=backend:py,checker:true sprite-exec prog.curry
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
  value with the choice unevaluated inside it).
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
  capsule flags the cells reachable from its arguments, and the cells a
  step, a pull-tab or a copy creates at a flagged cell inherit the flags).
  The tags define "argument-derived" for the checks of S0.  A replacement
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

The checker of the C++ runtime (``src/cyrt/checker.hpp``,
``src/cyrt/checker.cpp``) mirrors the Python checker hook by hook and check
by check.  Its header is outside the include closure of ``cyrt/cyrt.hpp``:
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
function) and the inductive position (``hnf``, at entry), and the entry of
a capsule (``evalS_step``).  The checker reads the state without changing
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
* A replacement by failure has three sources in the C++ runtime, where the
  Python backend has one.  An exempt leaf is one.  A failure at an
  inductive position is a completed step here (``hnf`` forwards the redex
  to the failure and the step returns; the Python backend unwinds, and its
  check never sees the step), and the check accepts it (B2 c names it).
  A return of a reference (``RET_REF``) forwards the redex to the node the
  reference denotes, which may be a failure; the tree tells such a leaf
  from the return of a built node, and the check accepts it (the Python
  backend writes a forward node there, which its check never sees).
* The write of rule S.x is a write into the slot of the variable
  (``*slot = genexpr``), not a copy of the spine, so the check is the
  memo's X-b (Inst-slot): the reduct of every configuration that references
  the redex is read before the write and compared after it, and no flags
  propagate (no cell is made).  The slot write of a generator that exists
  already (the ``has_generator`` branch of ``replace_freevar``, unhooked in
  the Python backend) is checked the same way (``slot_writes`` in the
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
  reads it by the group id), where the Python backend clones a generator
  for the variable first.
* The private copies that a set function makes for a configuration
  (``evalS_step``, the clone of a capsule) are not checked on either
  backend; the ``escape_all`` flag the Python checker reads is never set
  by the C++ runtime.

One defect is shared by the two checkers, found in the review of the C++
mirror.  The step propagation of the flags is a no-op on both backends:
the walk starts at the redex, which carries the flags, and stops there, so
a cell a step makes at a flagged redex inherits nothing (the pull-tabs,
the copies and the generators propagate).  The consequence: a boxed
argument whose evaluation outside the box, after the capsule started,
creates a choice gets a false report of S0 (E in A) at the pull-tab across
the box, on both backends.  The program (``lazyThenOutside2`` of the test
files)::

   g2 n = case n of { 1 -> Just (A ? B); _ -> Nothing }
   f2 x = 0 ? (case x of Just y -> case y of { A -> 1; B -> 2 })
   lazyThenOutside2 = let a = g2 (length [()]) in
     let vs = valuesOf (set1 f2 a) in (head vs, fromJust' a, vs)

The capsule yields 0 without demanding ``a``; the enclosing configuration
steps ``g2`` at the flagged cell, then ``?``, whose choice carries the tags
of the boxes above it and the flags of the ``?`` cell, which are none; the
second alternative of the capsule pulls the choice across the box.  The
runtime gives ``(0, A, [0, 1])`` and ``(0, B, [0, 2])``, the values of
weakly encapsulated search.  ``TestSharedArgument`` of both test files
pins the report as a known failure.  The fix is the owner's call, since it
changes what "argument-derived" reads: start the propagation of a step at
the successors of the result cell, under the budget of the walk, on both
backends.  Tried on the C++ checker, it removed the report on the three
shapes of the review and reported nothing on the 165 known-good goals.

``tests/unit_cxx_checker.py`` runs the known-good programs under the
checker, compiled and under ``interpret:all``, with the values and the
counters they have without it, and provokes one violation per check
through the debug entry points of the bindings
(``cyrtbindings.checker_debug_*``), which corrupt one configuration of a
runtime state on purpose or run one check on constructed nodes; the
entries refuse while the flag is off.  ``cyrtbindings.checker_counts``
gives the counts of the events a state saw.

The removal gate
----------------

Stage 6 of issue #82.  When the unit and functional suites pass under
``interpret:off``, ``tiered`` and ``all`` on the C++ backend for a month of
nightly runs, and no open bug names the Python backend as its only
reproduction, the source of the backend (``src/python/backends/py``), its
tests (the ``unit_py_*`` files, and the tests that skip or expect a failure
on one backend), its CI shard and the value ``py`` of the flag go in one
commit; the issue records the date.  The month started with the first
nightly run after the merge of stages 1 to 4.  Examples 03 and 04 and the
Python form of ``curry.save`` follow the decision on the C++ form.
