===========
Performance
===========

Sprite measures itself with the benchmark harness under
``tests/lib/benchmarks`` on the programs under
``tests/data/curry/benchmarks``.  Section 9 of ``tests/README`` describes
the suites, the records, and the comparison of two record files.  The
records of the performance program are under
``tests/data/curry/benchmarks/results``, one JSON Lines file per suite and
run, named by the label of the run.

The harness
===========

The driver is ``tests/run_benchmarks``.  A run names a suite, the
backends, the repetitions and the programs, and appends one record per
program and backend to a file:

.. code-block:: bash

    cd tests
    ./run_benchmarks -s throughput -b cxx -r 3 --label NAME -o NAME.jsonl
    ./run_benchmarks -s throughput --nightly -r 3 --timeout 300 -o t.jsonl
    ./run_benchmarks list -s throughput

The suites are:

* ``throughput``: the evaluation of ``main`` of each program in a new
  process.
* ``compile``: each program from source with the ICurry cache cold and
  warm, and the expression ``1+2``.
* ``import``: the start of the interpreter and the first imports.
* ``memory``: the peak memory with the collector on and off.
* ``split``: a search program whole and in parts.

Every run is a child process under a cap on its address space and
a timeout, in step mode of the rotation, so the counters of a record
reproduce.  A record holds the medians of the repetitions: wall and CPU
seconds, the peak resident set, the seconds of the evaluation alone, the
compile seconds, the counters steps, forks and collections, and the
instructions retired when ``perf`` is available.

Two record files are compared with:

.. code-block:: bash

    ./run_benchmarks compare OLD NEW
    ./run_benchmarks compare --deterministic OLD NEW

The counters must be equal: a change in them is a change in the program or
the compiler, not in the machine.  ``--deterministic`` decides by the
instructions, with the seconds as advisory ratios; CPU seconds decide only
on a quiet machine, and never across machines.

The records
===========

``baseline-2026-10-03``
    The baseline before the performance program, at commit ``1780ae09``,
    on a quiet 12-core x86-64 workstation: the four suites, the C++ backend
    with five repetitions, the Python backend with one, and PAKCS on nine
    programs.  On the C++ backend the 30 programs of the dissertation took
    between 0.43 s (``PaliFunPats``) and 42 s (``Psort``) of CPU.  On the
    Python backend 11 of them timed out at 120 s and two failed
    (``Reverse`` and ``ReverseUser``).  The two Poker programs failed on
    every backend for lack of the Curry preprocessor.

``phase2-2026-10-04``
    The record of the C++ backend after Phase 2 of the program: the
    in-place rewrite, the block heap, the weak free-variable table, the
    interpreter.  It was taken at commit ``00f5472a`` with the changes in
    the working tree, on the same machine with a load average near 2 from
    other work.  It holds the nightly set of ten programs, three
    repetitions, and the memory suite.  The table gives the throughput
    record, CPU seconds of the whole process, the seconds of the
    evaluation alone, and the peak resident set.

    ==============  ========  ========  ==========  =========  =============  ========
    Program            CPU s    eval s       steps      forks    collections   peak MB
    ==============  ========  ========  ==========  =========  =============  ========
    Tak1               1.302     1.131    33629915          0             30      67.9
    Fib                0.347     0.179     3500006          0              2     120.5
    Reverse            0.607     0.427     8407963          0              8      63.2
    Primes             2.299     2.125    61364444          0             64      64.9
    Queens10           1.736     1.558    54505073          0             54      63.4
    PermSort           5.001     4.786    12531154    1588167              9     327.5
    SearchQueens       4.977     4.768    41373250    1084883             20     316.2
    QueensSet          0.772     0.599     2152979     511583              3     110.2
    QueensSet9         5.330     4.990    12143480    2979048             11     337.0
    Last               0.432     0.263     3100017     300002              4      66.5
    ==============  ========  ========  ==========  =========  =============  ========

    The memory record of the same label runs each program with the
    collector on and off.  ``Tak1`` peaks at 67.8 MB with it and 1009 MB
    without.  ``Primes`` peaks at 65 MB and 1863 MB, and ``Queens10`` at
    63 MB and 1512 MB.  Both files are of schema 1, without the
    instructions column; a comparison by instructions needs a newer
    baseline.  The later entries
    of the ``TODO`` (the saturation of apply chains, the repair of the set
    functions, tiered execution) moved the counters of some of these
    programs; a compare against this record reports them.

The step cost
=============

The runtime counts a rewrite step at every return of a step function.
The dated entries of the ``TODO`` give these costs per completed step on
``Tak1`` (33.6 million steps):

* The rotation check of the scheduler: 3 instructions per step in step
  mode and 5 in time mode, over the build before the ticker.
* The write counters of the collector (``make GC_WRITE_COUNTERS=1``): 36
  instructions per step, which is why the default build leaves them out.
* The scheduler counters (``make COUNTERS=1``): one to three percent of
  the instructions and a word per node.

``sprite-exec --stats`` prints the steps of a run, and the column
``instr_m`` of the harness the instructions in millions, so the quotient
of a run is at hand.

Nightly history
===============

A scheduled GitHub Actions job (``.github/workflows/perf.yml``) runs the
harness every night on the C++ backend.  It runs the throughput suite on a
fixed set of ten programs with three repetitions, the compile suite on the
same programs and the expression item, and the import suite.  The same
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

Other systems
=============

The baseline record holds the CPU seconds of PAKCS on nine programs beside
the two backends of Sprite; ``run_benchmarks -b pakcs`` measures it.  This
page makes no claim against other compilers.
