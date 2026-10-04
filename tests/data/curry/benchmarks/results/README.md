# Benchmark records

One JSON Lines file per suite and run, written by `tests/run_benchmarks`
(see `tests/README`, section 8, for the fields and the compare tool).

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
