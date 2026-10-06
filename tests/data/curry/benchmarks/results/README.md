# Benchmark records

One JSON Lines file per suite and run, written by `tests/run_benchmarks`
(see `tests/README`, section 9, for the fields and the compare tool).

The files of baseline-2026-10-03 and phase2-2026-10-04 are records of
schema 1: they have no instructions column, and their meta names the
machine cpu and cpus.  The harness reads them; a comparison by
instructions needs a newer baseline.

## baseline-2026-10-03

The baseline of the performance program, taken on a quiet 12-core x86-64
workstation at commit `1780ae09` (Phase 0 of the program, before the
self-contained toolchain landed).

- `throughput`: the 30 dissertation programs. C++ backend: 5 repetitions,
  300 s timeout. Python backend: 1 repetition, 120 s timeout (11 programs
  time out, 2 fail). PAKCS: 3 repetitions, 300 s timeout, 9 programs only;
  the rest is deferred. PokerChoice and PokerFree need the Curry
  preprocessor `currypp`, which the machine lacks, and fail on every
  backend.
- `compile`: each program compiled from source with the ICurry cache cold
  and warm, plus the expression item, both backends, 3 repetitions.
- `import`: interpreter start, `import curry`, the Prelude import, and
  Hello end to end, both backends, 5 repetitions.
- `memory`: peak RSS per program with the node collector on and, on the
  C++ backend, off; 1 repetition, 120 s timeout. Programs that exhaust the
  6 GB address-space cap with the collector off are recorded as failures.

## phase2-2026-10-04

The record of the C++ backend after Phase 2 of the performance program
(the in-place rewrite, the block heap, the weak free-variable table, the
interpreter), taken on the same 12-core x86-64 workstation at commit
`00f5472a` with the Phase 2 changes in the working tree (`-dirty`). Other
users' processes kept the load average near 2 during the runs; the CPU
seconds of the throughput suite agree with runs on a quiet machine within
the noise band of the compare tool.

- `throughput`: the nightly set of ten programs (`--nightly`), 3
  repetitions, 300 s timeout.
- `memory`: the same ten programs with the collector on and off, 1
  repetition, 300 s timeout.

Every compare against `baseline-2026-10-03` reports changed counters, for
the Phase 1 changes (alias inlining, the cheap Variable) changed the steps
of every program. Phase 2 changed the counters of QueensSet alone: steps
2152081 to 2152979 and forks 511413 to 511583, because the in-place rewrite
(T4) moved the rotation cadence of the scheduler from the forward-chain
compressions to the completed steps. A later compare against this record
expects equal counters.

## apps-2026-10-06

The first record of the applications suite (`tests/README`, section 9):
the dependency solver of example 15 against resolvelib 1.2.1, the resolver
of pip, and the overload resolution of example 21 against a plain-Python
implementation of the same ranking.  Taken on the 12-core x86-64
workstation of the other records at commit `28f3bf5b` with the rewritten
example 15 and the suite itself in the working tree (`-dirty`).  Settings:
`./run_benchmarks -s applications -r 3 --timeout 600 --cap 4G`, the
instructions counted by perf, the rotation in step mode, the modules of
the examples compiled (interpret:off), resolvelib from a virtual
environment on PYTHONPATH.  The file holds the records of three runs of
that command on one day, appended in this order: the dependency item
through resolvelib 800/solvable; `overloads`; and `-b resolvelib
--variant 800/unsolvable dependency` (the first run reached the
wall-clock limit of its session during that item, whose runs take over
seven minutes each).  Another stream and the test runs of the same pass kept
the load average between 2 and 8 during the runs: the seconds of the
Python backend at 10 and 20 packages came out 4 to 80 percent above an
earlier, interrupted run at load 2, the C++ backend's within 20 percent.
clang was not installed on the machine, so the clang opponent of the
overloads item was not measured; the item skips without clang++.

The dependency item (median seconds of eval_wall, the time from the index
in Python data to the answer; "timeout" is a run past 600 s):

- 10 packages, solvable: cxx 0.083 s, py 5.6 s, resolvelib 0.38 ms
  (cxx 220x slower, py 14800x slower).
- 10 packages, unsolvable: cxx 0.063 s, py 1.8 s, resolvelib 0.74 ms
  (cxx 86x slower).
- 20 packages, solvable: cxx 0.105 s, py 19.8 s, resolvelib 0.58 ms
  (cxx 180x slower).
- 20 packages, unsolvable: cxx 0.23 s, py 59 s, resolvelib 1.3 ms
  (cxx 170x slower).
- 50 packages, solvable: cxx 2.0 s, py 463 s, resolvelib 1.2 ms
  (cxx 1700x slower).
- 50 packages, unsolvable: cxx 10.7 s, py timeout, resolvelib 30 ms
  (cxx 360x slower).
- 100 packages: cxx and py timeout in both cases; resolvelib 6.6 ms
  (solvable) and 1.0 ms (unsolvable).
- 200 packages: resolvelib 8.3 ms and 0.9 ms.  800 packages: resolvelib
  3.5 ms (solvable); in the unsolvable case resolvelib does not answer:
  it raises ResolutionTooDeep at its bound of a million rounds
  (`MAX_ROUNDS` in `apps/dependency.py`), 430 to 470 s into each of its
  three runs, and the record holds the item as failed.

The two sides agree on whether a plan exists, and every plan holds on its
index (`depindex.holds`; `TestCommittedApplications` checks both).  The
plans are the same at 10 and 20 packages and differ at 50: the solver of
the example takes the demands in the order it meets them, and resolvelib
resolves the package with the fewest candidates first and backjumps, so
under the same newest-first preference its first plan is another plan of
the same index (25 packages in its closure against 21).

The overloads item, 1000 distinct calls against one overload set of eight
candidates: cxx 2.08 s (2.1 ms per call, 8.67 million steps), py 80 s
(80 ms per call), plain Python 28 ms (28 us per call); cxx 75x slower
than plain Python, py 2900x.  The 1000 answers are the same on every side
(708 unique, 237 ambiguous, 55 without a viable function).  The overload
set is built once before the clock starts; a first probe that rebuilt the
eight candidates on every call inside the time measured 6.25 s on cxx.

Curry loses at every size, and there is no crossover: the solver of
example 15 searches more as the index grows, and resolvelib stays in
milliseconds up to 800 packages in every case but the one above.  The
Sprite
backends run the sizes 10 to 100 and resolvelib alone runs 200 and 800
(`SPRITE_DEPENDENCY_SIZES` and `DEPENDENCY_SIZES` in
`tests/lib/benchmarks/suites.py`).

## The nightly history

The nightly performance job appends its records to the branch
`perf-history` of the repository, not to this directory; `tests/README`,
section 9, describes the job, the history command, and the chart page.
