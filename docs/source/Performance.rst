Performance
===========

`Performance history <perf/index.html>`_ shows the nightly measurements:
CPU seconds, memory use and exact counters by program, with selectable
metrics, time ranges and comparisons. Section 9 of ``tests/README``
describes the benchmark suites and record format. The harness can also
measure PAKCS with ``run_benchmarks -b pakcs``; comparisons across machines
do not establish relative speed.

Nightly history
===============

A scheduled GitHub Actions job (``.github/workflows/perf.yml``) runs the
harness every night on the runtime.  It runs the throughput suite on a
fixed set of ten programs with three repetitions, the compile suite on the
same programs and the expression item, the import suite and the
applications suite: two programs of the examples against the tools of their
trade (the dependency solver of lesson 15 against resolvelib, the resolver
of pip and the overload resolution of lesson 21 against a plain-Python
implementation of the same ranking).  The same
measurement runs by hand with ``tests/run_benchmarks --nightly``.  The job
appends the records to the branch ``perf-history`` of the repository with
the command ``run_benchmarks history DIR FILE...`` and compares each record
with the previous one of its item in the summary of the run.  The numbers
come from shared runners and are advisory: the job never fails on a
timing, only on a run that failed.  Read the CPU seconds with the exact
counters, the rewrite steps and the forks: a change in them is a change in
the program or the compiler, not in the machine.

The page `Performance history <perf/index.html>`_ draws one figure per
suite from that branch: one small panel per program with the metric over
time, the last value, a hollow marker where the steps changed, a cross
where a run failed, a readout on hover with the commit and the counters,
and a table view of the last run of every item against the previous one.
The metric and the time range are selectable.  The page is plain HTML and
JavaScript; it reads ``points.json`` from the history branch.


The harness
===========

The driver is ``tests/run_benchmarks``.  A run names a suite, the
backends, the repetitions and the programs and appends one record per
program and backend to a file:

.. code-block:: bash

    tests/run_benchmarks -s throughput -b cxx -r 3 --label NAME -o NAME.jsonl
    tests/run_benchmarks -s throughput --nightly -r 3 --timeout 300 -o t.jsonl
    tests/run_benchmarks list -s throughput

The ``COUNTERS`` and ``GC_WRITE_COUNTERS`` builds add instructions to
every step, which is why the default build leaves them out.

The suites are:

* ``community``: value goals of the KiCS2 and Curry2Go community benchmarks,
  selected by qualified name. The manifest under
  ``tests/data/curry/benchmarks/community`` records exclusions.
* ``throughput``: the evaluation of ``main`` of each program in a new
  process.
* ``compile``: each program from source with the ICurry cache cold and
  warm and the expression ``1+2``.
* ``import``: the start of the interpreter and the first imports.
* ``memory``: the peak memory with the collector on and off.
* ``split``: a search program whole and in parts.
* ``applications``: the application programs beside opponent
  implementations in other tools (section 9 of ``tests/README``).

Every run is a child process under a cap on its address space and
a timeout, in step mode of the rotation, so the counters of a record
reproduce.  A record holds the medians of the repetitions: wall and CPU
seconds, the peak resident set, the seconds of the evaluation alone, the
compile seconds, the counters steps, forks and collections and the
instructions retired when ``perf`` is available.

Two record files are compared with:

.. code-block:: bash

    tests/run_benchmarks compare OLD NEW
    tests/run_benchmarks compare --deterministic OLD NEW

A comparison needs equal counters: a change in them is a change in the program or
the compiler, not in the machine.  ``--deterministic`` decides by the
instructions, with the seconds as advisory ratios; CPU seconds decide only
on a quiet machine and never across machines.


The records
===========

Committed records live under ``tests/data/curry/benchmarks/results``.
Their README describes each record and which counters changed since it
was measured. ``tests/run_benchmarks compare OLD NEW`` compares two files;
the nightly history holds the current state.
