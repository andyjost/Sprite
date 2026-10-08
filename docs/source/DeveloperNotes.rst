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
  (``unit_cxx_scheduler.py``, ``unit_setfunctions_bugs.py``); the C++
  backend passes it.
* A string built by :func:`curry.expr` is one ``_biString`` node, which
  prints as ``_biString 'hello'`` until its first step unfolds it; on the
  C++ backend it is the list of its characters.  The ``repr`` of a negative
  ``Float`` node differs between the backends.

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
