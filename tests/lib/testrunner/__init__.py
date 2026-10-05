'''
The test runner: runs the test files of the tests directory in child
processes, several at a time under a memory budget, and prints one line per
file and a summary table.

Usage, from the tests directory:

    ./run_tests [options] [PATTERN ...]

or, with tests/lib on PYTHONPATH:

    python -m testrunner [options] [PATTERN ...]

Say ``./run_tests -h`` for the options and see section 10 of tests/README.
The modules:

    cli.py        The command line and the course of one run.
    manifest.py   The manifest of durations and peaks (tests/manifest.json).
    selection.py  Which files run: patterns, the fast tier, --changed.
    procs.py      Processes: sessions, resident sets, kills, the memory
                  of the machine.
    scheduler.py  Admission under the budget and the width, the watchdog,
                  and the run loop.
    report.py     The status lines, the summary table, and the parse of
                  the unittest output.
    prepare.py    The sequential warm pass of the shared Curry products.
'''

import os

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDIR = os.path.normpath(os.path.join(HERE, '..', '..'))
ROOTDIR = os.path.dirname(TESTDIR)
DEFAULT_SPRITE_HOME = os.path.join(ROOTDIR, 'install')
MANIFEST_FILE = os.path.join(TESTDIR, 'manifest.json')
LOGDIR = os.path.join(TESTDIR, '.cache', 'runner')

BACKENDS = ('py', 'cxx')

MIB = 1024 ** 2
GIB = 1024 ** 3

# The width of a run without -j: how many files run at once.  One file at a
# time until a calibration run on a quiet machine fills the manifest.  Then
# the intended default is 'auto': the budget decides, up to the core count.
DEFAULT_JOBS = 1

# The budget without --mem: this fraction of MemAvailable at the start.
DEFAULT_MEM_FRACTION = 0.6

# The cap of a file is CAP_FACTOR times its manifest peak, at least MIN_CAP.
# A file without a peak in the manifest gets DEFAULT_CAP.
CAP_FACTOR = 2
MIN_CAP = 512 * MIB
DEFAULT_CAP = 2 * GIB

# The limit on the address space of a child (ulimit -v) is a backstop only.
# It is the larger of BACKSTOP and BACKSTOP_FACTOR times the cap of the file,
# unless SPRITE_TEST_MAX_VMEM_KB names a limit (or "unlimited").
BACKSTOP = 6 * GIB
BACKSTOP_FACTOR = 3

# Seconds after which a file is killed, without --timeout.
DEFAULT_TIMEOUT = 1800

# The fast tier: files whose manifest duration is below this many seconds.
DEFAULT_FAST_SECONDS = 5.0

# The watchdog polls the sessions of the running files this often.
POLL_SECONDS = 0.5
