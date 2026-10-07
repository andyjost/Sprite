'''
The suites and their measurement items.

An item is one measurement: a command to run in a child process, the
environment it runs in, and the way its numbers are read from its output.
The suites:

throughput
    ``sprite-exec -t --stats -m PROGRAM`` in the benchmark directory, or
    PAKCS with ``:set +time``.  The dissertation programs by default.
compile
    ``PROGRAM.curry`` copied to an empty directory and compiled without an
    evaluation (``sprite-exec --stats -g '' PROGRAM.curry``), with the
    ICurry cache cold (SPRITE_CACHE_FILE empty) and warm (a cache file of
    the harness, filled by the warm-up run).  The item ``expression``
    compiles ``1+2`` with curry.compile in a child Python (probe.py), cold
    and warm.
import
    ``python -c pass`` (item ``python``), ``import curry`` (``import``), the
    import of the Prelude (``prelude``), and Hello end to end (``hello``).
memory
    The throughput command with the collector on and, on the C++ backend,
    with the collector off (SPRITE_GC_THRESHOLD above any node count).
split
    A search program whole (the throughput command) and in parts: its
    search space split by hand into 2, 4, and 8 independent subproblems,
    each ``sprite-exec -t --stats -m PROGRAMSplit -g partK_I`` with the
    split directory on CURRYPATH.  The programs are those with a module
    under data/curry/benchmarks/split; the split command tabulates the
    records.
applications
    Two programs of the examples against the tools of their trade, in one
    process each, with the question and the data the same on every side
    (the child programs under apps/).  The item ``dependency`` asks the
    solver of example 15 for the first preferred plan of the root of a
    generated package index, newest first, or for the answer that no plan
    exists, against resolvelib, the resolver of pip, with a provider over
    the same index; the variants are SIZE/CASE for the sizes of
    DEPENDENCY_SIZES and the cases solvable and unsolvable.  The item
    ``overloads`` resolves OVERLOAD_CALLS distinct calls against one
    overload set with example 21, the overload set built once before the
    clock starts and the terms of the arguments of every call built from
    Python data inside the measured time, against a plain-Python
    implementation of the same ranking and, on request, against the
    overload resolution of clang under -ftime-trace.  The opponents are backends of the suite
    (OPPONENTS); the Sprite backends run the modules of the examples
    compiled (interpret:off) unless the environment names a mode.  An
    opponent that is not installed is skipped with a message.
'''

import fnmatch, glob, os, platform, shutil, subprocess, tempfile
from . import APPDIR, BACKENDS, CURRYDIR, DISSERTATION, HERE, NIGHTLY
from . import OPPONENTS, SPLITDIR, SUITES
from . import measure, records

__all__ = [
    'APPLICATIONS', 'COLLECTOR_OFF', 'DEFAULT_BACKENDS', 'DEFAULT_REPEAT'
  , 'DEPENDENCY_CASES', 'DEPENDENCY_SIZES', 'EXPRESSION', 'IMPORT_ITEMS'
  , 'Item', 'NIGHTLY_DEPENDENCY_SIZES', 'OPPONENTS_OF', 'OVERLOAD_CALLS'
  , 'SPLIT_PARTS', 'SPRITE_DEPENDENCY_SIZES', 'Settings', 'all_programs'
  , 'build', 'candidates', 'default_backends', 'dependency_sizes'
  , 'dependency_variants', 'nightly_items', 'select', 'set_backend_flag'
  , 'set_interpret_flag', 'split_programs', 'split_variants'
  ]

PROBE = os.path.join(HERE, 'probe.py')
# The child programs of the applications suite.
DEPENDENCY = os.path.join(APPDIR, 'dependency.py')
OVERLOADS = os.path.join(APPDIR, 'overloads.py')
CLANGPROBE = os.path.join(APPDIR, 'clangprobe.py')
# The expression of the compile suite and its Curry type.
EXPRESSION = ('1+2', 'Int')
# A node count that no program reaches: the collector never runs.
COLLECTOR_OFF = '1000000000'
IMPORT_ITEMS = ('python', 'import', 'prelude', 'hello')
# The part counts of the split suite.
SPLIT_PARTS = (2, 4, 8)
# The items of the applications suite and the opponents of each.
APPLICATIONS = ('dependency', 'overloads')
OPPONENTS_OF = {'dependency': ('resolvelib',), 'overloads': ('python', 'clang')}
# The sizes of the generated index of the dependency item (packages), the
# sizes the Sprite backends run (the solver of example 15 does not end
# within minutes above them; see the README of the records), and the sizes
# of the nightly job.
DEPENDENCY_SIZES = (10, 20, 50, 100, 200, 800)
SPRITE_DEPENDENCY_SIZES = (10, 20, 50, 100)
NIGHTLY_DEPENDENCY_SIZES = (10, 20, 50)
DEPENDENCY_CASES = ('solvable', 'unsolvable')
# The distinct calls of the overloads item.
OVERLOAD_CALLS = 1000
DEFAULT_REPEAT = {
    'throughput': 5, 'compile': 3, 'import': 5, 'memory': 1, 'split': 3
  , 'applications': 3
  }
# The backends of a run without -b: the C++ backend, and in the
# applications suite both Sprite backends with the opponents that need no
# compiler.
DEFAULT_BACKENDS = {'applications': ('cxx', 'py', 'resolvelib', 'python')}


def all_programs():
  '''The top-level programs of the benchmark directory, sorted.'''
  files = sorted(glob.glob(os.path.join(CURRYDIR, '*.curry')))
  return [os.path.basename(f)[:-len('.curry')] for f in files]


def split_programs():
  '''The programs with a split module under the split directory, sorted.'''
  suffix = 'Split.curry'
  files = sorted(glob.glob(os.path.join(SPLITDIR, '*' + suffix)))
  return [os.path.basename(f)[:-len(suffix)] for f in files]


def split_variants():
  '''The variants of the split suite: whole, then K/I for every part.'''
  return ['whole'] + ['%d/%d' % (k, i) for k in SPLIT_PARTS for i in range(k)]


def default_backends(suite):
  '''The backends of a run of ``suite`` without -b.'''
  return list(DEFAULT_BACKENDS.get(suite, ('cxx',)))


def dependency_sizes(backend, nightly=False):
  '''
  The sizes of the dependency item on ``backend``: every size for an
  opponent, the sizes that end for a Sprite backend, and the sizes of the
  nightly job with ``nightly``.
  '''
  if nightly:
    return list(NIGHTLY_DEPENDENCY_SIZES)
  if backend in BACKENDS:
    return list(SPRITE_DEPENDENCY_SIZES)
  return list(DEPENDENCY_SIZES)


def dependency_variants(backend, nightly=False):
  '''The variants SIZE/CASE of the dependency item on ``backend``.'''
  return [
      '%d/%s' % (size, case)
          for size in dependency_sizes(backend, nightly)
          for case in DEPENDENCY_CASES
    ]


def candidates(suite):
  '''
  The names a PROGRAM argument can select in ``suite``, and the names run
  without an argument.
  '''
  if suite == 'import':
    return list(IMPORT_ITEMS), list(IMPORT_ITEMS)
  if suite == 'split':
    return split_programs(), split_programs()
  if suite == 'applications':
    return list(APPLICATIONS), list(APPLICATIONS)
  programs = all_programs()
  default = [p for p in DISSERTATION if p in programs]
  if suite == 'compile':
    return programs + ['expression'], default + ['expression']
  return programs, default


def nightly_items(suite):
  '''
  The items of ``suite`` that the nightly performance job measures: the
  NIGHTLY programs, with the expression item in the compile suite; every
  item of the import suite; the split programs of the split suite.
  '''
  if suite == 'import':
    return list(IMPORT_ITEMS)
  if suite == 'split':
    return split_programs()
  if suite == 'applications':
    return list(APPLICATIONS)
  programs = all_programs()
  names = [p for p in NIGHTLY if p in programs]
  if suite == 'compile':
    names.append('expression')
  return names


def select(suite, patterns, nightly=False):
  '''
  The programs of ``suite`` that match the shell-style ``patterns``, in the
  order of the patterns; the default set without patterns.  With
  ``nightly`` the items of the nightly job take the place of both the
  candidates and the default set.
  '''
  if suite not in SUITES:
    raise ValueError('no suite %r' % suite)
  names, default = candidates(suite)
  if nightly:
    names = default = nightly_items(suite)
  if not patterns:
    return default
  selected = []
  for pattern in patterns:
    matches = fnmatch.filter(names, pattern)
    if not matches:
      raise ValueError(
          'no program of the %s suite matches %r' % (suite, pattern)
        )
    selected.extend(m for m in matches if m not in selected)
  return selected


# The rotation mode of a measured run; see Settings.environment.
STEP_MODE = 'steps:65536'

def set_backend_flag(flags, backend):
  '''SPRITE_INTERPRETER_FLAGS with the backend set and the other flags kept.'''
  kept = [
      f for f in (flags or '').split(',')
        if f and not f.startswith('backend:')
    ]
  return ','.join(['backend:%s' % backend] + kept)


def set_interpret_flag(flags, mode):
  '''
  SPRITE_INTERPRETER_FLAGS with the flag ``interpret`` set to ``mode``
  unless the flags name a mode already: the environment of the run wins.
  '''
  if any(f.startswith('interpret:') for f in (flags or '').split(',')):
    return flags
  return ','.join([f for f in (flags or '').split(',') if f] + ['interpret:' + mode])


class Settings:
  '''
  The settings of a run: the tools, the limits, the environment.  ``perf``
  is the path of perf for the repetition that counts the instructions, or
  None for no such repetition; ``instructions_source`` says how the
  instructions are counted, or why they are not, for the records.
  '''
  def __init__(
      self, sprite_home, pakcs=None, timeout=600, cap=None, env=None, label=''
    , warmup=1, perf=None, instructions_source=None
    ):
    self.sprite_home = os.path.abspath(sprite_home)
    self.pakcs = pakcs
    self.timeout = timeout
    self.cap = cap
    self.env = dict(env or {})
    self.label = label
    self.warmup = warmup
    self.perf = perf
    if instructions_source is None:
      instructions_source = 'perf stat -e %s' % measure.PERF_EVENT if perf \
                            else 'not measured'
    self.instructions_source = instructions_source

  @property
  def sprite_exec(self):
    return os.path.join(self.sprite_home, 'bin', 'sprite-exec')

  @property
  def python(self):
    return os.path.join(self.sprite_home, 'bin', 'python')

  def environment(self, backend, **extra):
    '''
    The environment of a child: the variables of the harness over the
    inherited ones.  The backend flag is set; other interpreter flags of
    the environment are kept.  The rotation of the C++ backend is in step
    mode unless the environment or -e names a mode (an empty value counts
    as unset), so that the counters steps and forks reproduce between
    records (the flag ``rotation`` in curry.interpreter.flags).
    '''
    env = dict(os.environ)
    env.update(self.env)
    env['SPRITE_HOME'] = self.sprite_home
    env['PYTHONIOENCODING'] = 'utf-8'
    if backend in ('cxx', 'py'):
      env['SPRITE_INTERPRETER_FLAGS'] = set_backend_flag(
          env.get('SPRITE_INTERPRETER_FLAGS'), backend
        )
      if not env.get('SPRITE_ROTATION'):
        env['SPRITE_ROTATION'] = STEP_MODE
      # The warnings of the Curry front end off (overlapping rules; see
      # curry.toolchain._frontend): a cold run compiles, a warm one does
      # not, and the output of a record should not tell them apart.
      if not env.get('SPRITE_FRONTEND_WARNINGS'):
        env['SPRITE_FRONTEND_WARNINGS'] = '0'
    env.update(extra)
    return env

  def has_resolvelib(self):
    '''
    Whether the Python of the installation imports resolvelib; detected
    once.  The package is not part of Sprite: pip install resolvelib, or
    put a virtual environment that has it on PYTHONPATH.
    '''
    if not hasattr(self, '_resolvelib'):
      try:
        proc = subprocess.run(
            [self.python, '-c', 'import resolvelib'], env=self.environment('py')
          , capture_output=True, text=True, timeout=120
          )
        self._resolvelib = proc.returncode == 0
      except (OSError, subprocess.TimeoutExpired):
        self._resolvelib = False
    return self._resolvelib

  @staticmethod
  def clang():
    '''The path of clang++, or None.'''
    return shutil.which('clang++')

  def run(self, cmd, env, cwd, perf=False):
    '''Runs one command; under perf when ``perf`` is set and perf is known.'''
    return measure.run_command(
        cmd, env=env, cwd=cwd, timeout=self.timeout, cap=self.cap
      , perf=self.perf if perf else None
      )

  def metadata(self):
    '''
    Facts about the machine and the tools, stored in every record.  The
    machine context, cpu_model, cores, and mem_gb, names no host.
    '''
    return {
        'python': self._version(
            [self.python, '-c', 'import sys; print(sys.version.split()[0])']
          )
      , 'compiler': self._version(
            [os.path.join(self.sprite_home, 'tools', 'cxx'), '--version']
          )
      , 'frontend': self._frontend()
      , 'cpu_model': records.cpu_model()
      , 'cores': os.cpu_count()
      , 'mem_gb': records.memory_gb()
      , 'platform': '%s-%s-%s' % (
            platform.system(), platform.release(), platform.machine()
          )
      , 'rss_source': measure.rss_source()
      , 'instructions_source': self.instructions_source
      , 'timeout': self.timeout
      , 'cap': self.cap
      , 'env': self.env
      }

  @staticmethod
  def _version(cmd):
    '''The first line a command prints, or None.'''
    try:
      proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
      return None
    lines = proc.stdout.strip().splitlines()
    return lines[0].strip() if proc.returncode == 0 and lines else None

  def _frontend(self):
    '''The Curry system of the installed library, from its sysconfig.'''
    filename = os.path.join(self.sprite_home, 'sysconfig', 'currylib_version')
    try:
      with open(filename) as stream:
        return 'pakcs-' + stream.read().strip()
    except OSError:
      return None


class Item:
  '''
  One measurement.  ``command`` gives the command, the environment, and the
  working directory of one run, fresh for every run when the item needs a
  clean directory; ``parse`` reads the numbers of a run; ``cleanup`` runs
  after each run.
  '''
  suite = None
  variant = None

  def __init__(self, program, backend, settings):
    self.program = program
    self.backend = backend
    self.settings = settings

  @property
  def key(self):
    return (self.suite, self.program, self.backend, self.variant)

  def warmup(self):
    '''The number of warm-up runs, not recorded.'''
    return self.settings.warmup

  def command(self):
    raise NotImplementedError

  def parse(self, run):
    return {}

  def cleanup(self):
    pass

  def unavailable(self):
    '''
    One line that says why the item cannot run on this machine (a tool it
    needs is missing), or None when it can.  The run command skips such an
    item and writes no record for it.
    '''
    return None

  def measure(self, perf=False):
    '''
    Runs the item once and returns the sample; under perf, which counts the
    instructions, when ``perf`` is set.
    '''
    cmd, env, cwd = self.command()
    try:
      run = self.settings.run(cmd, env, cwd, perf=perf)
      return records.sample(run, self.parse(run))
    finally:
      self.cleanup()


def stats_fields(run):
  '''The fields of a sample that come from the line of sprite-exec --stats.'''
  stats = measure.parse_stats(run.stderr)
  if stats is None:
    return {}
  return {
      'steps': stats['steps'], 'forks': stats['forks']
    , 'collections': stats['collections'], 'compile': stats['compile']
    , 'extra': {'stats': stats}
    }


class SpriteExecItem(Item):
  '''``sprite-exec -t --stats -m MODULE`` in the benchmark directory.'''
  suite = 'throughput'
  extra_env = {}

  @property
  def module(self):
    return self.program

  def command(self):
    cmd = [self.settings.sprite_exec, '-t', '--stats', '-m', self.module]
    env = self.settings.environment(
        self.backend, CURRYPATH=CURRYDIR, **self.extra_env
      )
    return cmd, env, CURRYDIR

  def parse(self, run):
    fields = {'eval_wall': measure.parse_time(run.stdout)}
    fields.update(stats_fields(run))
    return fields


class PakcsItem(Item):
  '''PAKCS loads the module and evaluates main with ``:set +time``.'''
  suite = 'throughput'

  def command(self):
    cmd = [
        self.settings.pakcs, ':set', '+time', ':l', self.program, ':eval'
      , 'main', ':q'
      ]
    env = self.settings.environment('pakcs', CURRYPATH=CURRYDIR)
    return cmd, env, CURRYDIR

  def parse(self, run):
    times = measure.parse_pakcs(run.stdout)
    if times is None:
      return {}
    cpu, wall = times
    return {'eval_cpu': cpu, 'eval_wall': wall}


class MemoryItem(SpriteExecItem):
  '''The throughput command with the collector on or off.'''
  suite = 'memory'

  def __init__(self, program, backend, settings, variant):
    super().__init__(program, backend, settings)
    self.variant = variant
    if variant == 'collector=off':
      self.extra_env = {'SPRITE_GC_THRESHOLD': COLLECTOR_OFF}


class SplitItem(SpriteExecItem):
  '''
  The whole of a search program (the throughput command), or one part of
  its search space split by hand: ``sprite-exec -t --stats -m PROGRAMSplit
  -g partK_I``, with the split directory on CURRYPATH.  The variant names
  the part: whole, or K/I for part I of K.
  '''
  suite = 'split'

  def __init__(self, program, backend, settings, variant):
    super().__init__(program, backend, settings)
    self.variant = variant

  @property
  def part(self):
    '''The part count and the index of a part; None for the whole.'''
    if self.variant == 'whole':
      return None
    k, i = self.variant.split('/')
    return int(k), int(i)

  @property
  def module(self):
    return self.program if self.part is None else self.program + 'Split'

  def command(self):
    cmd, env, cwd = super().command()
    if self.part is not None:
      cmd += ['-g', 'part%d_%d' % self.part]
      env['CURRYPATH'] = os.pathsep.join([SPLITDIR, CURRYDIR])
    return cmd, env, cwd


class CommandItem(Item):
  '''The Python of the installation with a one-line program.'''
  suite = 'import'
  CODE = {
      'python': 'pass'
    , 'import': 'import curry'
    , 'prelude': "import curry; curry.import_('Prelude')"
    }

  def command(self):
    cmd = [self.settings.python, '-c', self.CODE[self.program]]
    return cmd, self.settings.environment(self.backend), CURRYDIR


class HelloItem(SpriteExecItem):
  '''Hello end to end: start, imports, load, one step, exit.'''
  suite = 'import'
  module = 'Hello'


class CacheVariant:
  '''
  An item with a cold and a warm variant of the ICurry cache.  Cold runs
  without the cache; a warm run uses a cache file of the harness, which the
  warm-up run fills, so warm items have at least one warm-up run.  Every run
  works in a fresh directory, so no earlier output is current.
  '''
  def __init__(self, program, backend, settings, variant, workdir):
    super().__init__(program, backend, settings)
    self.variant = variant
    self.workdir = workdir
    self.tmpdir = None

  def warmup(self):
    if self.variant == 'cold':
      return 0
    return max(1, self.settings.warmup)

  def cache_file(self):
    if self.variant == 'cold':
      return ''
    return os.path.join(self.workdir, 'icurry.db')

  def make_tmpdir(self):
    self.tmpdir = tempfile.mkdtemp(prefix='compile-', dir=self.workdir)
    return self.tmpdir

  def cleanup(self):
    if self.tmpdir is not None:
      shutil.rmtree(self.tmpdir, ignore_errors=True)
      self.tmpdir = None


class ModuleCompileItem(CacheVariant, Item):
  '''``PROGRAM.curry`` compiled from source in an empty directory.'''
  suite = 'compile'

  def command(self):
    tmpdir = self.make_tmpdir()
    source = self.program + '.curry'
    shutil.copy(os.path.join(CURRYDIR, source), tmpdir)
    cmd = [self.settings.sprite_exec, '--stats', '-g', '', source]
    env = self.settings.environment(
        self.backend, SPRITE_CACHE_FILE=self.cache_file()
      )
    return cmd, env, tmpdir

  def parse(self, run):
    return stats_fields(run)


class ExpressionItem(CacheVariant, Item):
  '''curry.compile of an expression in a child Python, to its first value.'''
  suite = 'compile'

  def command(self):
    tmpdir = self.make_tmpdir()
    cmd = [self.settings.python, PROBE] + list(EXPRESSION)
    env = self.settings.environment(
        self.backend, SPRITE_CACHE_FILE=self.cache_file()
      )
    return cmd, env, tmpdir

  def parse(self, run):
    probe = measure.parse_json(run.stdout)
    if probe is None:
      return {}
    stats = probe.get('stats') or {}
    return {
        'compile': probe.get('compile'), 'eval_wall': probe.get('first_value')
      , 'steps': stats.get('steps'), 'forks': stats.get('forks')
      , 'collections': stats.get('collections'), 'extra': {'probe': probe}
      }


def probe_fields(run, time_field):
  '''
  The fields of a sample from the JSON object that a child program of the
  applications suite prints: the measured seconds as eval_wall, the
  counters of curry.stats() on a Sprite backend, and the whole object under
  extra.probe.  An empty dict when the child printed none.
  '''
  probe = measure.parse_json(run.stdout)
  if probe is None:
    return {}
  stats = probe.get('stats') or {}
  return {
      'eval_wall': probe.get(time_field), 'steps': stats.get('steps')
    , 'forks': stats.get('forks'), 'collections': stats.get('collections')
    , 'extra': {'probe': probe}
    }


class ApplicationItem(Item):
  '''
  An item of the applications suite: a child program under apps/ run by
  the Python of the installation, on a Sprite backend or on an opponent.
  On a Sprite backend the modules of the examples run compiled
  (interpret:off) unless the environment names a mode.
  '''
  suite = 'applications'
  # The field of the JSON object with the measured seconds.
  time_field = 'solve'

  def environment(self):
    env = self.settings.environment(self.backend)
    if self.backend in ('cxx', 'py'):
      env['SPRITE_INTERPRETER_FLAGS'] = set_interpret_flag(
          env['SPRITE_INTERPRETER_FLAGS'], 'off'
        )
    return env

  def parse(self, run):
    return probe_fields(run, self.time_field)

  def unavailable(self):
    if self.backend == 'resolvelib' and not self.settings.has_resolvelib():
      return 'resolvelib is not importable by the Python of the ' \
             'installation (pip install resolvelib)'
    if self.backend == 'clang' and not self.settings.clang():
      return 'clang++ is not on PATH'
    return None


class DependencyItem(ApplicationItem):
  '''
  The first preferred plan of a generated package index: the solver of
  example 15 on a Sprite backend, or resolvelib.  The variant is
  SIZE/CASE.
  '''
  def __init__(self, backend, settings, size, case):
    super().__init__('dependency', backend, settings)
    self.size = size
    self.case = case
    self.variant = '%d/%s' % (size, case)

  def command(self):
    side = 'resolvelib' if self.backend == 'resolvelib' else 'sprite'
    cmd = [self.settings.python, DEPENDENCY, side, str(self.size), self.case]
    return cmd, self.environment(), APPDIR


class OverloadsItem(ApplicationItem):
  '''
  OVERLOAD_CALLS distinct calls resolved against one overload set: example
  21 on a Sprite backend, the plain-Python ranking (backend python), or
  clang under -ftime-trace (backend clang).
  '''
  def __init__(self, backend, settings):
    super().__init__('overloads', backend, settings)

  def command(self):
    if self.backend == 'clang':
      cmd = [self.settings.python, CLANGPROBE, str(OVERLOAD_CALLS)]
    else:
      side = 'python' if self.backend == 'python' else 'sprite'
      cmd = [self.settings.python, OVERLOADS, side, str(OVERLOAD_CALLS)]
    return cmd, self.environment(), APPDIR


def build(suite, programs, backends, settings, workdir, nightly=False):
  '''
  The items of ``suite`` for ``programs`` on ``backends``, in run order: the
  backends and variants of one program follow each other, so that a drift of
  the machine hits them alike.  ``workdir`` is a directory for the files of
  the compile suite.  ``nightly`` selects the sizes of the nightly job in
  the applications suite.
  '''
  if suite not in SUITES:
    raise ValueError('no suite %r' % suite)
  for backend in backends:
    if backend not in BACKENDS + OPPONENTS:
      raise ValueError('no backend %r' % backend)
    if backend in OPPONENTS and suite != 'applications':
      raise ValueError(
          'the %s backend is available in the applications suite only'
          % backend
        )
  if 'pakcs' in backends:
    if suite != 'throughput':
      raise ValueError(
          'the pakcs backend is available in the throughput suite only'
        )
    if not settings.pakcs:
      raise ValueError('the pakcs backend needs a PAKCS executable (--pakcs)')
  items = []
  for program in programs:
    if suite == 'applications':
      # The backends of one size and case follow each other.
      sides = [
          b for b in backends
            if b not in OPPONENTS or b in OPPONENTS_OF[program]
        ]
      if program == 'dependency':
        sizes = sorted(set(
            size for b in sides for size in dependency_sizes(b, nightly)
          ))
        for size in sizes:
          for case in DEPENDENCY_CASES:
            for backend in sides:
              if size in dependency_sizes(backend, nightly):
                items.append(DependencyItem(backend, settings, size, case))
      else:
        for backend in sides:
          items.append(OverloadsItem(backend, settings))
      continue
    for backend in backends:
      if suite == 'throughput':
        cls = PakcsItem if backend == 'pakcs' else SpriteExecItem
        items.append(cls(program, backend, settings))
      elif suite == 'memory':
        items.append(MemoryItem(program, backend, settings, 'collector=on'))
        if backend == 'cxx':
          items.append(MemoryItem(program, backend, settings, 'collector=off'))
      elif suite == 'compile':
        cls = ExpressionItem if program == 'expression' else ModuleCompileItem
        for variant in 'cold', 'warm':
          items.append(cls(program, backend, settings, variant, workdir))
      elif suite == 'import':
        cls = HelloItem if program == 'hello' else CommandItem
        items.append(cls(program, backend, settings))
      elif suite == 'split':
        for variant in split_variants():
          items.append(SplitItem(program, backend, settings, variant))
  return items
