'''
The prepare pass: a sequential warm pass over the shared Curry products.

The tests compile the modules under tests/data/curry into product
directories (.curry/<subdir>/) beside the sources.  Every file of a run
reads the same products, and a file writes one only when it is missing or
stale.  Two files that write the same product at once can leave a torn file
for a third to read: the front end, the ICurry writer, the JSON writer, and
the C++ compiler all write in place (see section 10 of README).  The ICurry
cache is safe: SQLite with a busy timeout.

So the pass runs sprite-make, one directory at a time and one process at a
time, for the backend of the run, before any file starts.  After it, the
parallel files find their products current and only read them.  A module
that fails to compile is reported in the log of the pass, not fatal: the
test that needs it reports the failure in its own terms.

The pass covers the shared pool (tests/data/curry) and the corpus of each
selected functional test (CORPUS).  The examples under examples/ are left
to unit_examples.py, which alone compiles them; the scheduler never runs the
two backends of one file at once.
'''

import os
from . import TESTDIR
from .scheduler import Job

__all__ = ['CORPUS', 'EXCLUDE', 'directories', 'jobs', 'modules']

# Every file may use the pool.
ANY = None

# The directories of Curry sources, relative to the tests directory, the
# extra entries of the Curry path they need, and the test files that use
# them (ANY for the pool).
CORPUS = [
    ('data/curry', (), ANY)
  , ('data/curry/benchmarks', (), ('unit_cxx_variable.py', 'unit_benchmarks.py'))
  , ('data/curry/eqconstr', (), ('func_eqconstr.py',))
  , ('data/curry/examples', (), ('func_examples.py',))
  , ('data/curry/funpat', (), ('func_funpat.py',))
  , ('data/curry/io', (), ('func_io.py',))
  , ('data/curry/kiel', ('data/curry/kiel/lib',), ('func_kiel.py',))
  , ('data/curry/math', (), ('func_math.py',))
  , ('data/curry/readshow', (), ('func_readshow.py',))
  , ('data/curry/residuation', (), ('func_residuation.py',))
  , ('data/curry/setfunctions', (), ('func_setfunctions.py',))
  , ('data/curry/smap', (), ('func_smap.py',))
  ]

# Sources that must fail to compile, or that need a tool the machine may
# lack.  A test checks the failure: badimport imports a module that does
# not exist; helloExternal declares an external function that no backend
# resolves (unit_icurry.py).  PokerChoice and PokerFree of the benchmark
# programs need the Curry preprocessor currypp (see
# data/curry/benchmarks/results/README.md); the harness compiles them in
# its warm-up and records the failure itself.
EXCLUDE = {
    'badimport.curry', 'helloExternal.curry', 'PokerChoice.curry'
  , 'PokerFree.curry'
  }

# The target of sprite-make per backend.  Compact, zipped JSON is what an
# import writes, so the products are the same files.
TARGET = {'py': '--py', 'cxx': '--so'}

def directories(selected):
  '''
  The entries of CORPUS that the selected files use: the pool and the
  corpus of each selected functional test.
  '''
  selected = set(selected)
  return [
      entry for entry in CORPUS
            if entry[2] is ANY or selected.intersection(entry[2])
    ]

def modules(directory, testdir=TESTDIR):
  '''The Curry sources directly in ``directory``, sorted, minus EXCLUDE.'''
  path = os.path.join(testdir, directory)
  try:
    names = os.listdir(path)
  except FileNotFoundError:
    return []
  # The product directory .curry ends with the suffix as well: only a file
  # is a module.
  return sorted(
      os.path.join(directory, name) for name in names
          if name.endswith('.curry') and name not in EXCLUDE
          and os.path.isfile(os.path.join(path, name))
    )

def command(sprite_home, backend, files):
  '''The sprite-make command that makes ``files`` for ``backend``.'''
  make = os.path.join(sprite_home, 'bin', 'sprite-make')
  return [make, '-k', '-q', '-c', '-z', TARGET[backend]] + list(files)

def jobs(
    selected, backends, sprite_home, env, logdir, cap, timeout, prefix=()
  , testdir=TESTDIR
  ):
  '''
  One job per directory and backend, in the order of CORPUS.  ``env`` is the
  environment of the run; CURRYPATH gets the extra entries of the directory
  in front.  ``prefix`` is the command prefix (the address-space backstop).
  '''
  result = []
  for backend in backends:
    for directory, extras, _ in directories(selected):
      files = modules(directory, testdir)
      if not files:
        continue
      jobenv = dict(env)
      path = [os.path.join(testdir, extra) for extra in extras]
      path.append(os.path.join(testdir, directory))
      if jobenv.get('CURRYPATH'):
        path.append(jobenv['CURRYPATH'])
      jobenv['CURRYPATH'] = ':'.join(path)
      label = 'prepare ' + directory
      logfile = os.path.join(
          logdir, backend, 'prepare-%s.log' % directory.replace('/', '-')
        )
      result.append(Job(
          label, backend, list(prefix) + command(sprite_home, backend, files)
        , cap=cap, timeout=timeout, logfile=logfile, cwd=testdir, env=jobenv
        , exclusive=True
        ))
  return result
