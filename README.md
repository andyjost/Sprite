# Performance history

The nightly performance job of Sprite writes this branch, perf-history.
It is not meant to be edited by hand.

- `records/SUITE.jsonl`: every record of the suite, one JSON object per
  line, in the order of arrival.  The fields are documented in
  `tests/lib/benchmarks/records.py` of the main branch, and
  `tests/run_benchmarks compare` reads these files as they are.
- `points.json`: the points of the chart page: one compact object per
  record, derived from the record files by `tests/run_benchmarks history`.

The page `perf/index.html` of the documentation reads `points.json` from
this branch.  Timings from shared runners are advisory; the exact counters
(steps, forks) tell a change in the program from a change in the machine.
