# Benchmark records

One JSON Lines file per suite and run, written by `tests/run_benchmarks`
(see `tests/README`, section 9, for the fields and the compare tool).

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

## The nightly history

The nightly performance job appends its records to the branch
`perf-history` of the repository, not to this directory; `tests/README`,
section 9, describes the job, the history command, and the chart page.
