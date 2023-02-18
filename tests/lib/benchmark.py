import collections, os, pprint, sys, time, timeit
import curry
from curry import config
import subprocess

OUTPUT_FILE = 'benchmark_data.py'
REPEAT = 2
EXEC = config.sprite_exec()
CURRYDIR = os.path.normpath(config.installed_path('../tests/data/curry/benchmarks'))

def run_curry(mode, cymodule):
  if mode in ['cxx', 'py']:
    cmd = ' '.join([
        'CURRYPATH=%s' % CURRYDIR, 'SPRITE_INTERPRETER_FLAGS=backend:%s' % mode
      , EXEC, '-m', cymodule
      , '> /dev/null'
      ])
  elif mode == 'pakcs':
    cmd = 'cd %s; pakcs :l %s :eval main :q > /dev/null' % (CURRYDIR, cymodule)
  t = timeit.timeit(lambda: os.system(cmd), number=1)
  return t


class Reporter(object):
  def __init__(self, repeat=REPEAT):
    self.repeat = repeat
    self.data = collections.defaultdict(dict)

  def test_context(self, name):
    return TestContext(self, name)


class TestContext(object):
  def __init__(self, reporter, name):
    self.reporter = reporter
    self.name = name
    assert name not in self.reporter.data

  def __enter__(self, *args):
    print(self.name)
    return self

  def __exit__(self, *args):
    pass

  def mode(self, mode):
    return ModeContext(self, mode)

class ModeContext(object):
  def __init__(self, tc, mode):
    self.tc = tc
    self.mode = mode
    self.best = float('inf')

  def __enter__(self, *args):
    sys.stdout.write('    %-16s ' % self.mode)
    sys.stdout.flush()
    return self

  def __exit__(self, *args):
    self.tc.reporter.data[self.tc.name][self.mode] = self.best
    sys.stdout.write('  |  %0.3f\n' % self.best)

  def report(self, sec):
    self.best = min(self.best, sec)
    sys.stdout.write('%7.3f  ' % sec)
    sys.stdout.flush()


def measure(reporter, cymodule):
  '''
  Compile and run a Curry proram, passing results to the specified reporter.
  '''
  with reporter.test_context(cymodule) as tc:
    for mode in ['cxx', 'pakcs']:
      with tc.mode(mode) as mc:
        for t in range(reporter.repeat):
          t = run_curry(mode, cymodule)
          mc.report(t)


R = Reporter()
measure(R, 'rev')
# with open(OUTPUT_FILE, 'w') as report:
#   report.write(pprint.pformat(dict(R.data)))
#   print("Results written to ", OUTPUT_FILE)
