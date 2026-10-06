===========
Performance
===========

Sprite measures itself with the benchmark harness under
``tests/lib/benchmarks`` on the programs under
``tests/data/curry/benchmarks``.  Section 9 of ``tests/README`` describes
the suites, the records, and the comparison of two record files.  The
records of the baseline of the performance program are under
``tests/data/curry/benchmarks/results``.

Nightly history
===============

A scheduled GitHub Actions job (``.github/workflows/perf.yml``) runs the
harness every night on the C++ backend: the throughput suite on a fixed set
of ten programs with three repetitions, the compile suite on the same
programs and the expression item, the import suite, and the applications
suite, two programs of the examples against the tools of their trade (the
dependency solver of example 15 against resolvelib, the resolver of pip,
and the overload resolution of example 21 against a plain-Python
implementation of the same ranking).  The same
measurement runs by hand with ``tests/run_benchmarks --nightly``.  The job
appends the records to the branch ``perf-history`` of the repository and
compares each record with the previous one of its item in the summary of
the run.  The numbers come from shared runners and are advisory: the job
never fails on a timing, only on a run that failed.  Read the CPU seconds
with the exact counters, the rewrite steps and the forks: a change in them
is a change in the program or the compiler, not in the machine.

The page `Performance history <perf/index.html>`_ draws one figure per
suite from that branch: one small panel per program with the metric over
time, the last value, a hollow marker where the steps changed, a cross
where a run failed, a readout on hover with the commit and the counters,
and a table view of the last run of every item against the previous one.
The metric and the time range are selectable.  The page is plain HTML and
JavaScript; it reads ``points.json`` from the history branch.
