'''Functional tests for the equational constraint.'''
import cytest # from ./lib; must be first
from glob import glob
import curry
import cytest.oracle
import functools
import os

SOURCE_DIR = 'data/curry/eqconstr/'

# Failing tests.  To determine the curent set of failures, clear this list and
# run.
SKIP = set()
failed = set()

def noteSkipped(f):
  '''Record the tests that fail.'''
  @functools.wraps(f)
  def skipper(self, modulename):
    try:
      f(self, modulename)
    except:
      failed.add(modulename)
      raise
  return skipper

class TestEqConstr(cytest.TestCase):
  def setUp(self):
    super(TestEqConstr, self).setUp()
    curry.path.insert(0, SOURCE_DIR)

  @classmethod
  def tearDownClass(cls):
    if failed:
      print 'The following tests failed.  ' \
            'Copy this line into func_eqconstr.py to skip them.'
      print 'SKIP =', failed

  # Create a test for every file under the source directory.
  for cysrc in glob(SOURCE_DIR + '*.curry'):
    name = os.path.splitext(os.path.split(cysrc)[-1])[0]
    if name not in SKIP:
      locals()['test_'+name] = lambda self, name=name: self.check(name)

  @cytest.oracle.require
  @noteSkipped
  def check(self, modulename):
    '''
    Load the specified module, execute each goal, and compare with goldens
    provided by the oracle.
    '''
    module = curry.import_(modulename)
    goals = [
        v for k,v in module.__dict__.items()
          if k.startswith('goal') or k.startswith('main')
      ]
    num = 0
    for goal in sorted(goals, key=lambda x: x.ident.basename):
      if goal.info.arity:
        continue
      num += 1
      goldenfile = os.path.join(SOURCE_DIR, goal.ident + '.au-gen')
      cytest.oracle.divine(
          module, goal, [SOURCE_DIR], '20s', goldenfile=goldenfile
        )
      sprite_result = cytest.oracle.cyclean(
          '\n'.join(map(str, curry.eval(goal))+[''])
        )
      self.compareEqualToFile(sprite_result, goldenfile)
    self.assertGreater(num, 0)
