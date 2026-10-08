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
parallel files find their products current and only read them.  The pass
is advisory.  sprite-make runs with -k, so a module that fails to compile
does not stop the others, and the job of its directory ends ``incomplete``
rather than ``FAILED``: the note of the job names the modules that have no
product after the pass (the .py or the .so of the backend; the JSON on the
C++ backend under the interpreter flag ``interpret`` set to new or all,
where sprite-make --so ends), :func:`summary` prints one line about the
whole pass, and the exit status of the run does not depend on it.  The
test that needs the module reports the failure in its own terms.  A failed
compile that leaves an old product in place is not seen; that test reports
it too.

The pass covers the shared pool (tests/data/curry) and the corpus of each
selected functional test (CORPUS).  The examples under examples/ are left
to unit_examples.py, which alone compiles them; the scheduler never runs the
two backends of one file at once.

After the pass the runner prunes its own product cache
(:func:`prune_product_cache`): the cache under tests/.cache/products, which
the runner sets unless the environment names a directory, keeps the entries
of the installed runtime alone, so the directory (and the CI cache entry
that carries it) does not grow with every change to the runtime headers.  A
cache the environment named is left alone: it may serve other
installations.
'''

import os, re, subprocess
from . import TESTDIR
from .scheduler import Job

__all__ = [
    'CACHE_LINE', 'CORPUS', 'DEFAULT_PRODUCT_CACHE', 'EXCLUDE', 'JSON_PRODUCTS'
  , 'PRODUCT', 'PRUNE', 'PrepareJob', 'cache_counts', 'corpus_owners'
  , 'directories', 'interpret_flag', 'jobs', 'modules', 'product_subdir'
  , 'product_suffixes', 'prune_product_cache', 'summary'
  ]

# The product cache of a run unless the environment names one
# (cli.environment).  The runner prunes this one and no other.
DEFAULT_PRODUCT_CACHE = os.path.join(TESTDIR, '.cache', 'products')

# The program that prunes the product cache, run in the Python of the
# installation: it keeps the digests of the installed runtime, the release
# and the debug flavor, and prints the two counts of _productcache.prune
# (nothing goes when the installation has no digest: no headers).
PRUNE = '''
from curry.backends.cxx import toolchain
from curry.toolchain import _productcache
keep = {toolchain.object_digest(), toolchain.object_digest('debug')}
print(*_productcache.prune(keep))
'''

def prune_product_cache(sprite_home, env):
  '''
  Prunes the product cache of the run when it is the runner's own
  (DEFAULT_PRODUCT_CACHE in ``env``): the digest directories of other
  runtimes and the leftovers of an interrupted store go (PRUNE;
  _productcache.prune).  Returns the pair of counts, or None when the
  cache is another one, is off, or the program failed.
  '''
  root = env.get('SPRITE_PRODUCT_CACHE')
  if not root or os.path.abspath(root) != DEFAULT_PRODUCT_CACHE:
    return None
  if not os.path.isdir(root):
    return None
  python = os.path.join(sprite_home, 'bin', 'python')
  try:
    proc = subprocess.run(
        [python, '-B', '-c', PRUNE], capture_output=True, text=True, env=env
      , timeout=300
      )
  except (OSError, subprocess.TimeoutExpired):
    return None
  if proc.returncode != 0:
    return None
  try:
    digests, temporaries = proc.stdout.split()
    return int(digests), int(temporaries)
  except ValueError:
    return None

# The line sprite-make prints at the end of a run that restored a product
# from the product cache or stored one there (curry.tools.make.cache_line).
# The pass runs sprite-make without -q, so the line reaches the log, and the
# job reads its counts from there.
CACHE_LINE = re.compile(
    r'^\S+: product cache: (?P<restored>\d+) restored, (?P<stored>\d+) stored$'
  , re.MULTILINE
  )

def cache_counts(text):
  '''
  The counts of the product cache in the output ``text`` of sprite-make:
  the products restored and the products stored, summed over its lines.
  None when the text holds no such line.
  '''
  found = CACHE_LINE.findall(text)
  if not found:
    return None
  return (
      sum(int(restored) for restored, _ in found)
    , sum(int(stored) for _, stored in found)
    )

# Every file may use the pool.
ANY = None

# The directories of Curry sources, relative to the tests directory, the
# extra entries of the Curry path they need, and the test files that use
# them (ANY for the pool).
CORPUS = [
    ('data/curry', (), ANY)
  , ( 'data/curry/benchmarks', ()
    , ( 'unit_benchmarks.py', 'unit_cxx_heap.py', 'unit_cxx_passthrough.py'
      , 'unit_cxx_variable.py'
      )
    )
  , ( 'data/curry/eqconstr', ()
    , ( 'func_eqconstr.py', 'func_eqconstr_a0.py', 'func_eqconstr_a0b0c0_1.py'
      , 'func_eqconstr_a0b0c0_2.py', 'func_eqconstr_a0b0c0_3.py'
      , 'func_eqconstr_a2b1c0.py'
      )
    )
  , ('data/curry/examples', (), ('func_examples.py',))
  , ('data/curry/funpat', (), ('func_funpat.py',))
  , ('data/curry/io', (), ('func_io.py',))
  , ('data/curry/kiel', ('data/curry/kiel/lib',), ('func_kiel.py',))
  , ( 'data/curry/math', ()
    , ('func_math.py', 'func_math_int.py', 'func_math_float.py')
    )
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

# The suffix of the final product of a module per backend, in the product
# directory (product_subdir) beside the source.
PRODUCT = {'py': '.py', 'cxx': '.so'}

# The JSON of a module, which ends the plan of sprite-make --so under the
# interpreter flag ``interpret`` set to new or all: the runtime interprets
# the module from it, and no object is written (Json2Cpp.ends_plan of the
# C++ toolchain).  The pass asks for zipped JSON (-z); the plain form is
# accepted too.
JSON_PRODUCTS = ('.json.z', '.json')

def interpret_flag(flags):
  '''
  The value of the flag ``interpret`` in a SPRITE_INTERPRETER_FLAGS value:
  off, new, or all.  Off when the flag is absent.
  '''
  for item in (flags or '').split(','):
    name, _, value = item.partition(':')
    if name.strip() == 'interpret' and value.strip():
      return value.strip()
  return 'off'

def product_suffixes(backend, flags=None):
  '''
  The suffixes of the final product of a module on ``backend`` under the
  interpreter flags ``flags`` (a SPRITE_INTERPRETER_FLAGS value): one of
  them exists after a pass that made the module.  The C++ backend under
  interpret:new or interpret:all ends at the JSON.
  '''
  if backend == 'cxx' and interpret_flag(flags) in ('new', 'all'):
    return JSON_PRODUCTS
  return (PRODUCT[backend],)

def corpus_owners():
  '''
  The test files that CORPUS names: each compiles a corpus of its own on a
  cold tree.  The fast tier leaves them out (selection.compiles_corpus).
  '''
  return sorted(set(
      name for _, _, owners in CORPUS if owners is not ANY for name in owners
    ))

def product_subdir(sprite_home, env=None):
  '''
  The product directory of the installation, relative to the directory of
  a module: what ``sprite-make -S`` prints (.curry/sprite-<frontend>).  None
  when sprite-make cannot say.
  '''
  make = os.path.join(sprite_home, 'bin', 'sprite-make')
  try:
    proc = subprocess.run(
        [make, '-S'], capture_output=True, text=True, env=env, timeout=120
      )
  except (OSError, subprocess.TimeoutExpired):
    return None
  subdir = proc.stdout.strip()
  return subdir if proc.returncode == 0 and subdir else None

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
  '''
  The sprite-make command that makes ``files`` for ``backend``.  Without
  -q: the line about the product cache must reach the log (cache_counts),
  and the warnings of the front end are off through the environment of the
  run (SPRITE_FRONTEND_WARNINGS; cli.environment).
  '''
  make = os.path.join(sprite_home, 'bin', 'sprite-make')
  return [make, '-k', '-c', '-z', TARGET[backend]] + list(files)

def _names(modules, limit=6):
  '''The base names of some modules, the first ``limit`` of them.'''
  names = [os.path.basename(module) for module in modules]
  if len(names) > limit:
    return '%s and %d more' % (', '.join(names[:limit]), len(names) - limit)
  return ', '.join(names)

class PrepareJob(Job):
  '''
  The job of one directory on one backend: advisory.  ``modules`` are the
  sources it makes, relative to ``testdir``; ``subdir`` is the product
  directory relative to the directory of a module, or None when unknown.
  After the run, a job that did not end well names the modules without a
  product in its note.
  '''

  def __init__(self, directory, modules, subdir, testdir, *args, **kwds):
    super().__init__(*args, advisory=True, **kwds)
    self.directory = directory
    self.modules = list(modules)
    self.subdir = subdir
    self.testdir = testdir
    # The products restored from the product cache and stored there, read
    # from the log after the run (cache_counts); None when the log says
    # nothing about the cache.
    self.restored = None
    self.stored = None

  @property
  def flags(self):
    '''The SPRITE_INTERPRETER_FLAGS of the environment of the job, or None.'''
    return (self.env or {}).get('SPRITE_INTERPRETER_FLAGS')

  def products(self, module):
    '''
    The files of which one is the product of ``module`` on the backend of
    the job, under its interpreter flags (product_suffixes); empty when the
    product directory is unknown.
    '''
    if self.subdir is None:
      return []
    directory, name = os.path.split(module)
    stem = name[:-len('.curry')] if name.endswith('.curry') else name
    return [
        os.path.join(self.testdir, directory, self.subdir, stem + suffix)
        for suffix in product_suffixes(self.backend, self.flags)
      ]

  def product(self, module):
    '''The usual product of ``module``: the first of ``products``, or None.'''
    products = self.products(module)
    return products[0] if products else None

  def missing(self):
    '''
    The modules without a product, in the order of ``modules``; None when
    the product directory is unknown.
    '''
    if self.subdir is None:
      return None
    return [
        module for module in self.modules
               if not any(os.path.isfile(f) for f in self.products(module))
      ]

  def read_cache_counts(self):
    '''Reads the counts of the product cache from the log (cache_counts).'''
    if not self.logfile:
      return
    try:
      with open(self.logfile, 'r', errors='replace') as stream:
        found = cache_counts(stream.read())
    except OSError:
      return
    if found is not None:
      self.restored, self.stored = found

  def on_finished(self):
    self.read_cache_counts()
    details = []
    if self.restored:
      details.append(
          '%d of %d from the product cache' % (self.restored, len(self.modules))
        )
    if self.status != 'ok':
      missing = self.missing()
      if missing is None:
        details.append('see the log')
      elif not missing:
        details.append('every product is present')
      else:
        details.append('%d of %d modules without a product: %s' % (
            len(missing), len(self.modules), _names(missing)
          ))
    if details:
      detail = '; '.join(details)
      self.note = '%s; %s' % (self.note, detail) if self.note else detail

def summary(jobs):
  '''
  One line about the pass: the modules and the directories, and the modules
  without a product after it.  ``jobs`` may hold other jobs; they are
  skipped.
  '''
  jobs = [job for job in jobs if isinstance(job, PrepareJob)]
  if not jobs:
    return 'prepare: nothing to make'
  backends = sorted(set(job.backend for job in jobs))
  # Every backend makes the same directories: count those of the first.
  first = [job for job in jobs if job.backend == backends[0]]
  modules = sum(len(job.modules) for job in first)
  head = 'prepare: %d module%s in %d director%s on %s' % (
      modules, '' if modules == 1 else 's', len(first)
    , 'y' if len(first) == 1 else 'ies', '+'.join(backends)
    )
  restored = sum(job.restored or 0 for job in jobs)
  if restored:
    head += ', %d from the product cache' % restored
  missing = []
  unknown = []
  for job in jobs:
    if job.status == 'ok' or not job.finished:
      continue
    found = job.missing()
    if found is None:
      unknown.append(job)
    else:
      missing.extend('%s (%s)' % (module, job.backend) for module in found)
  if not missing and not unknown:
    return head + ', every product present'
  parts = [head]
  if missing:
    shown = missing[:8]
    if len(missing) > len(shown):
      shown.append('%d more' % (len(missing) - len(shown)))
    parts.append('%d without a product: %s' % (len(missing), ', '.join(shown)))
  if unknown:
    parts.append(
        '%d director%s did not end well, products unknown: see the log'
      % (len(unknown), 'y' if len(unknown) == 1 else 'ies')
      )
  parts.append('the tests that need them report it')
  return '; '.join(parts)

def jobs(
    selected, backends, sprite_home, env, logdir, cap, timeout, prefix=()
  , testdir=TESTDIR, subdir=None
  ):
  '''
  One job per directory and backend, in the order of CORPUS.  ``env`` is the
  environment of the run; CURRYPATH gets the extra entries of the directory
  in front.  ``prefix`` is the command prefix (the address-space backstop).
  ``subdir`` is the product directory (product_subdir), for the check of
  the products after the run.
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
      result.append(PrepareJob(
          directory, files, subdir, testdir
        , label, backend, list(prefix) + command(sprite_home, backend, files)
        , cap=cap, timeout=timeout, logfile=logfile, cwd=testdir, env=jobenv
        , exclusive=True
        ))
  return result
