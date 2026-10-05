'''
Benchmark harness: measures Sprite and PAKCS on the programs under
tests/data/curry/benchmarks and writes one JSON record per measurement.

Usage, from the tests directory:

    ./run_benchmarks [run] [options] [PROGRAM ...]
    ./run_benchmarks compare OLD NEW [options]
    ./run_benchmarks counters FILE [options]
    ./run_benchmarks split FILE [options]
    ./run_benchmarks history DIR [FILE ...] [options]
    ./run_benchmarks list [--suite NAME] [--nightly]

or, from anywhere, with the Python of an installation and tests/lib on
PYTHONPATH:

    python -m benchmarks [run|compare|counters|split|history|list] ...

Say ``./run_benchmarks -h`` and ``./run_benchmarks compare -h`` for the
options.  The modules:

    suites.py    The suites and the measurement items they consist of.
    measure.py   Runs one child process under a cap and a timeout and reads
                 its numbers.
    records.py   The record format, the medians, and the JSON Lines files.
    run.py       The command that runs a suite and writes the records.
    compare.py   The command that compares two record files.
    counters.py  The command that tabulates the scheduler counters of a
                 record file (a runtime built with make COUNTERS=1).
    split.py     The command that tabulates the records of the split suite:
                 the speedup bound and the duplicated work of a search
                 program split by hand into parts.
    history.py   The command that keeps the history of the nightly job: it
                 appends record files to a history directory, compares
                 each record with the previous one of its item, and writes
                 the points of the chart page.
    probe.py     The child program of the expression item.
'''

import os

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDIR = os.path.normpath(os.path.join(HERE, '..', '..'))
ROOTDIR = os.path.dirname(TESTDIR)
CURRYDIR = os.path.join(TESTDIR, 'data', 'curry', 'benchmarks')
# The search programs split by hand for the split suite.
SPLITDIR = os.path.join(CURRYDIR, 'split')
DEFAULT_SPRITE_HOME = os.path.join(ROOTDIR, 'install')

SUITES = ('throughput', 'compile', 'import', 'memory', 'split')
BACKENDS = ('cxx', 'py', 'pakcs')

# The programs of Chapter 7 of the dissertation.  The README of the benchmark
# directory maps the names of the figures to the files.
DISSERTATION = (
    'Half', 'Hamming', 'Fib', 'Palindrome', 'Peano', 'Primes', 'Psort'
  , 'Qsortlet', 'Queens10', 'Quicksort', 'Reverse', 'ReverseBuiltin'
  , 'ReverseGroups', 'ReverseHO', 'ReverseUser', 'SearchMAC', 'Tak1'
  , 'TakPeano', 'ColormapChoice', 'ColormapFree', 'Horseman', 'Last'
  , 'PaliFunPats', 'PermSort', 'PermSortPeano', 'PokerChoice', 'PokerFree'
  , 'QueensSet', 'RegExp', 'SearchQueens'
  )

# The fixed set of the nightly performance job (--nightly; see the README
# of the tests, section 9): ten programs that cover deterministic
# recursion and lazy lists, nondeterminism with fingerprints, narrowing
# with free variables, set functions with a heavy collector share, and
# functional patterns, each in seconds on the C++ backend.
NIGHTLY = (
    'Tak1', 'Fib', 'Reverse', 'Primes', 'Queens10', 'PermSort', 'SearchQueens'
  , 'QueensSet', 'QueensSet9', 'Last'
  )
