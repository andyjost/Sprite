# Benchmark programs

This directory holds the Curry programs used to benchmark Sprite.  Every
top-level `*.curry` file defines a goal `main`.  The subdirectories
(`completeness/`, `composite/`, `failing/`, `toofast/`) hold programs that are
not part of the timed set; `split/` holds three search programs split by
hand into parts for the split suite of the harness (below).

## Programs from the dissertation

Chapter 7 of the dissertation reports execution times for the programs below.
Three names differ from the figures:

- `Tak` is now `Tak1.curry` (`tak 27 16 8`, the middle row of Figure 7.2).
- `Queens(10)` is now `Queens10.curry`.
- `Primes.curry` was deleted in 2023 and has been restored from the repository
  history.

Figure 7.1, deterministic programs (18):

| Figure 7.1       | File                   |
|------------------|------------------------|
| Half             | `Half.curry`           |
| Hamming          | `Hamming.curry`        |
| Fib              | `Fib.curry`            |
| Palindrome       | `Palindrome.curry`     |
| Peano            | `Peano.curry`          |
| Primes           | `Primes.curry`         |
| Psort            | `Psort.curry`          |
| Qsortlet         | `Qsortlet.curry`       |
| Queens(10)       | `Queens10.curry`       |
| Quicksort        | `Quicksort.curry`      |
| Reverse          | `Reverse.curry`        |
| ReverseBuiltin   | `ReverseBuiltin.curry` |
| ReverseGroups    | `ReverseGroups.curry`  |
| ReverseHO        | `ReverseHO.curry`      |
| ReverseUser      | `ReverseUser.curry`    |
| SearchMAC        | `SearchMAC.curry`      |
| Tak              | `Tak1.curry`           |
| TakPeano         | `TakPeano.curry`       |

Figure 7.3, non-deterministic programs (12).  An `S` marks a program that uses
set functions.

| Figure 7.3       | File                   |
|------------------|------------------------|
| ColormapChoice   | `ColormapChoice.curry` |
| ColormapFree     | `ColormapFree.curry`   |
| Horseman         | `Horseman.curry`       |
| Last             | `Last.curry`           |
| PaliFunPats      | `PaliFunPats.curry`    |
| PermSort         | `PermSort.curry`       |
| PermSortPeano    | `PermSortPeano.curry`  |
| PokerChoice (S)  | `PokerChoice.curry`    |
| PokerFree (S)    | `PokerFree.curry`      |
| QueensSet (S)    | `QueensSet.curry`      |
| RegExp           | `RegExp.curry`         |
| SearchQueens     | `SearchQueens.curry`   |

## Timing one program with Sprite

Stage Sprite first (`make stage`).  Then, from the repository root, set
`CURRYPATH` to this directory and run the module with the C++ backend.  The
`-t` option suppresses the program output and prints the execution time in
seconds; `--stats` adds one line on standard error with the wall and CPU
seconds of the process, the rewrite steps, the forks, the collections, the
peak RSS, and the compile seconds:

    CURRYPATH=tests/data/curry/benchmarks \
    SPRITE_INTERPRETER_FLAGS=backend:cxx \
    install/bin/sprite-exec -t --stats -m Fib

To measure several programs, use the harness.  From `tests/`, say
`./run_benchmarks -h` for the options.  By default, it runs the 30 programs
of the dissertation five times each on the C++ backend and writes one JSON
record per program:

    cd tests
    ./run_benchmarks -o cxx.jsonl             # the dissertation programs, cxx
    ./run_benchmarks -o some.jsonl Fib Tak1 Queens10
    ./run_benchmarks -b py -b cxx -r 3 -o both.jsonl Fib
    ./run_benchmarks -b pakcs -o pakcs.jsonl Fib   # PAKCS of the installation
    ./run_benchmarks compare cxx.jsonl later.jsonl

Other suites (`-s compile`, `-s import`, `-s memory`) measure the compile
times, the start-up times, and the peak memory.  Section 9 of `tests/README`
describes the suites, the records, and the comparison.  The harness is the
package `tests/lib/benchmarks`.

The harness runs the C++ backend in step mode (`SPRITE_ROTATION=steps:65536`
in the environment of every run): the scheduler rotates its alternatives
every 65536 completed steps, so the counters `steps` and `forks` of a record
reproduce exactly.  The tools default to time mode, where a ticker thread
paces the rotation on wall time (10 ms); a run by hand in time mode may
report other counters for a search program.  To measure time mode with the
harness, say `-e SPRITE_ROTATION=time:10ms`; to time one program by hand as
the harness does, set `SPRITE_ROTATION=steps:65536`.

## Scheduler counters

A runtime built with `make COUNTERS=1` reports, in the `--stats` line, how
the scheduler used its queue: the steps taken while the queue held one
configuration (the serial fraction), the steps inside set functions, the
steps on a redex that another configuration created (the shared work), the
largest queue, and the lifetimes of the configurations.  The harness keeps
the fields in every record, and `./run_benchmarks counters FILE` prints one
row per program.  The sprite-exec page of the documentation describes the
fields.  Sixteen of the thirty dissertation programs never fork, so their
serial fraction is 1; the search programs fork at almost every step and
their configurations live a few steps.

## The process-split experiment

The modules under `split/` are the inputs of the split suite
(`./run_benchmarks -s split`), the process-split experiment of the
parallel-evaluation gate.  Each spells the whole program and its search
space split by hand into 2, 4, and 8 parts, as the goals `main` and
`part2_0` .. `part8_7`; the harness runs the whole and every part in a
process of its own, and `./run_benchmarks split FILE` tabulates the speedup
bound (the whole over the longest part) and the duplicated work (the sum of
the parts over the whole).  `PermSortSplit` fixes the first binary choices
of the search (the insertions of 3, 4, and 5 into the growing permutation);
`SearchQueensSplit` fixes the position of the first element (the length of
the free list `u`); `QueensSetSplit` fixes the first element of the
permutation (the branch of `ndinsert`).  The parts of a split partition the
search space; `part n k i` and `permsPart n k i` take the size, and
`tests/unit_split.py` checks the partition at a small size.  Section 9 of
`tests/README` describes the suite and the command.

## The collector and the timings

The collector of the C++ backend runs by default (see `SPRITE_GC_THRESHOLD`
and `SPRITE_GC_GROWTH` in the documentation of the environment variables).
`QueensSet9` runs slower with it than without it (about 8 s against 5.5 s):
its set functions are consumed only in part, so every collection frees
queues of alternatives and their nodes, and the evaluation after a sweep
allocates from the free lists in scattered order.  The other programs run as
fast or faster, with a far smaller peak memory.  To time a program with the
collector off, set a threshold that no program reaches:

    SPRITE_GC_THRESHOLD=1000000000 CURRYPATH=tests/data/curry/benchmarks \
    SPRITE_INTERPRETER_FLAGS=backend:cxx install/bin/sprite-exec -t -m PermSort

## Running the programs with PAKCS or KiCS2

Ten programs import `Control.SetFunctions`:

    Itinerary, LongestSubstring, Matching, PokerChoice, PokerFree, QueensSet,
    QueensSet9, QueensSet10, ValidParens, Xform

Sprite ships this module in its own Curry library.  PAKCS 3.4.1 does not.  To
run these programs with PAKCS 3.4.1, install the CPM package `setfunctions`:

    cypm update
    cypm add setfunctions

`cypm add` records the dependency in the PAKCS home package, so plain `pakcs`
then finds the module.  The CPM bundled with PAKCS 3.4.1 points at a package
index that may no longer answer.  If `cypm update` cannot reach the index, put
these two lines in `~/.cpmrc` and rerun:

    PACKAGEINDEXURL=https://cpm.curry-lang.org/PACKAGES/INDEX.tar.gz
    PACKAGETARFILESURL=https://cpm.curry-lang.org/PACKAGES

PAKCS 3.9 and later (and current KiCS2) provide the module under the name
`Control.Search.SetFunctions`.  With those systems, change the import line
accordingly.

To time a program with PAKCS, say:

    cd tests/data/curry/benchmarks
    pakcs :set +time :l Fib :eval main :q
