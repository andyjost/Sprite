import pprint, sys, time
import code

OUTPUT_FILE = 'benchmark_data.py'
REPEAT = 1

def take_all(gen):
  for _ in gen:
    pass

def run_curry(cymodule, goal='main'):
  import curry, timeit
  CURRYDIR = './data/curry/benchmarks'
  curry.path.insert(0, CURRYDIR)
  mod = curry.import_(cymodule)
  expr = curry.expr(getattr(mod, goal))
  comp = curry.eval(expr)
  t = timeit.timeit(lambda: take_all(comp), number=1)
  return t


class Reporter(object):
  def __init__(self, repeat=5):
    self.repeat = REPEAT
    self.data = {}

  def context(self, name):
    return Context(self, name)

class Context(object):
  def __init__(self, reporter, name):
    self.reporter = reporter
    self.name = name
    self.best = float('inf')
    assert name not in self.reporter.data

  def __enter__(self, *args):
    sys.stdout.write('%-16s ' % self.name)
    return self

  def __exit__(self, *args):
    self.reporter.data[self.name] = self.best
    sys.stdout.write('  |  %0.3f\n' % self.best)

  def report(self, sec):
    self.best = min(self.best, sec)
    sys.stdout.write('%7.3f  ' % sec)
    sys.stdout.flush()


def measure(reporter, cymodule, goal='main'):
  '''
  Compile and run a Curry proram, passing results to the specified reporter.
  '''
  with reporter.context(cymodule) as cxt:
    for t in range(reporter.repeat):
      # t = t / 10 + 0.2
      # time.sleep(t)
      t = run_curry(cymodule, goal)
      cxt.report(t)


R = Reporter()
measure(R, 'rev')
with open(OUTPUT_FILE, 'w') as report:
  report.write(pprint.pformat(R.data))
  print("Results written to ", OUTPUT_FILE)
