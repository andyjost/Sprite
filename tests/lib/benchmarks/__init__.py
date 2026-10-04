'''
Benchmark harness: measures Sprite and PAKCS on the programs under
tests/data/curry/benchmarks and writes one JSON record per measurement.

Usage, from the tests directory:

    ./run_benchmarks [run] [options] [PROGRAM ...]
    ./run_benchmarks compare OLD NEW [options]
    ./run_benchmarks counters FILE [options]
    ./run_benchmarks list [--suite NAME]

or, from anywhere, with the Python of an installation and tests/lib on
PYTHONPATH:

    python -m benchmarks [run|compare|counters|list] ...

Say ``./run_benchmarks -h`` and ``./run_benchmarks compare -h`` for the
options.  The modules:

    suites.py    The four suites and the measurement items they consist of.
    measure.py   Runs one child process under a cap and a timeout and reads
                 its numbers.
    records.py   The record format, the medians, and the JSON Lines files.
    run.py       The command that runs a suite and writes the records.
    compare.py   The command that compares two record files.
    counters.py  The command that tabulates the scheduler counters of a
                 record file (a runtime built with make COUNTERS=1).
    probe.py     The child program of the expression item.
'''

import os

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDIR = os.path.normpath(os.path.join(HERE, '..', '..'))
ROOTDIR = os.path.dirname(TESTDIR)
CURRYDIR = os.path.join(TESTDIR, 'data', 'curry', 'benchmarks')
DEFAULT_SPRITE_HOME = os.path.join(ROOTDIR, 'install')

SUITES = ('throughput', 'compile', 'import', 'memory')
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
