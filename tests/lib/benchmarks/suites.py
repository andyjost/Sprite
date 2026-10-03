'''
The four suites and their measurement items.

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
'''

import fnmatch, glob, os, platform, shutil, subprocess, tempfile
from . import BACKENDS, CURRYDIR, DISSERTATION, HERE, SUITES
from . import measure, records

__all__ = [
    'COLLECTOR_OFF', 'DEFAULT_REPEAT', 'EXPRESSION', 'IMPORT_ITEMS', 'Item'
  , 'Settings', 'all_programs', 'build', 'candidates', 'select'
  , 'set_backend_flag'
  ]

PROBE = os.path.join(HERE, 'probe.py')
# The expression of the compile suite and its Curry type.
EXPRESSION = ('1+2', 'Int')
# A node count that no program reaches: the collector never runs.
COLLECTOR_OFF = '1000000000'
IMPORT_ITEMS = ('python', 'import', 'prelude', 'hello')
DEFAULT_REPEAT = {'throughput': 5, 'compile': 3, 'import': 5, 'memory': 1}


def all_programs():
  '''The top-level programs of the benchmark directory, sorted.'''
  files = sorted(glob.glob(os.path.join(CURRYDIR, '*.curry')))
  return [os.path.basename(f)[:-len('.curry')] for f in files]


def candidates(suite):
  '''
  The names a PROGRAM argument can select in ``suite``, and the names run
  without an argument.
  '''
  if suite == 'import':
    return list(IMPORT_ITEMS), list(IMPORT_ITEMS)
  programs = all_programs()
  default = [p for p in DISSERTATION if p in programs]
  if suite == 'compile':
    return programs + ['expression'], default + ['expression']
  return programs, default


def select(suite, patterns):
  '''
  The programs of ``suite`` that match the shell-style ``patterns``, in the
  order of the patterns; the default set without patterns.
  '''
  if suite not in SUITES:
    raise ValueError('no suite %r' % suite)
  names, default = candidates(suite)
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


def set_backend_flag(flags, backend):
  '''SPRITE_INTERPRETER_FLAGS with the backend set and the other flags kept.'''
  kept = [
      f for f in (flags or '').split(',')
        if f and not f.startswith('backend:')
    ]
  return ','.join(['backend:%s' % backend] + kept)


class Settings:
  '''The settings of a run: the tools, the limits, the environment.'''
  def __init__(
      self, sprite_home, pakcs=None, timeout=600, cap=None, env=None, label=''
    , warmup=1
    ):
    self.sprite_home = os.path.abspath(sprite_home)
    self.pakcs = pakcs
    self.timeout = timeout
    self.cap = cap
    self.env = dict(env or {})
    self.label = label
    self.warmup = warmup

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
    the environment are kept.
    '''
    env = dict(os.environ)
    env.update(self.env)
    env['SPRITE_HOME'] = self.sprite_home
    env['PYTHONIOENCODING'] = 'utf-8'
    if backend != 'pakcs':
      env['SPRITE_INTERPRETER_FLAGS'] = set_backend_flag(
          env.get('SPRITE_INTERPRETER_FLAGS'), backend
        )
    env.update(extra)
    return env

  def run(self, cmd, env, cwd):
    return measure.run_command(
        cmd, env=env, cwd=cwd, timeout=self.timeout, cap=self.cap
      )

  def metadata(self):
    '''Facts about the machine and the tools, stored in every record.'''
    return {
        'python': self._version(
            [self.python, '-c', 'import sys; print(sys.version.split()[0])']
          )
      , 'compiler': self._version(
            [os.path.join(self.sprite_home, 'tools', 'cxx'), '--version']
          )
      , 'frontend': self._frontend()
      , 'cpu': records.cpu_model()
      , 'cpus': os.cpu_count()
      , 'platform': '%s-%s-%s' % (
            platform.system(), platform.release(), platform.machine()
          )
      , 'rss_source': measure.rss_source()
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

  def measure(self):
    '''Runs the item once and returns the sample.'''
    cmd, env, cwd = self.command()
    try:
      run = self.settings.run(cmd, env, cwd)
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


def build(suite, programs, backends, settings, workdir):
  '''
  The items of ``suite`` for ``programs`` on ``backends``, in run order: the
  backends and variants of one program follow each other, so that a drift of
  the machine hits them alike.  ``workdir`` is a directory for the files of
  the compile suite.
  '''
  if suite not in SUITES:
    raise ValueError('no suite %r' % suite)
  for backend in backends:
    if backend not in BACKENDS:
      raise ValueError('no backend %r' % backend)
  if 'pakcs' in backends:
    if suite != 'throughput':
      raise ValueError(
          'the pakcs backend is available in the throughput suite only'
        )
    if not settings.pakcs:
      raise ValueError('the pakcs backend needs a PAKCS executable (--pakcs)')
  items = []
  for program in programs:
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
  return items
