'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first
from glob import glob
import curry
import cytest.compare
import functools
import os

SOURCE_DIR = 'data/curry/kiel/'

# Failing tests.
SKIP = set((
    'Imports', 'ModConc', 'account', 'accountport', 'addnamedserver', 'addserver'
  , 'addtimeoutserver', 'allsols', 'arithseq', 'assembler', 'best', 'calc'
  , 'checkbutton', 'chords', 'circuit', 'colormap', 'colormap_nd', 'config'
  , 'counter', 'counter_controlled', 'daVinciTest', 'diamond', 'digit', 'england'
  , 'escher_cond', 'escher_higher', 'escher_perm', 'events', 'expr_parser'
  , 'family_con', 'family_nd', 'family_rel', 'first', 'fractal', 'hello'
  , 'higher', 'hilbert', 'horseman', 'httpget', 'infresiduate', 'inputmask'
  , 'iodemo', 'last', 'magicseries', 'mail', 'mailsearch', 'member', 'menu'
  , 'mergesort', 'mortgage', 'nameserver', 'nats', 'nondetfunc', 'palindrome'
  , 'philo', 'prolog', 'psort', 'putModuleHead', 'queens', 'radiotraffic'
  , 'relational', 'rigidadd', 'scrollbar', 'search', 'sema', 'sierpinski'
  , 'smm', 'sportsdb', 'sudoku', 'talk', 'temperature', 'textappend'
  , 'textstyledappend'
  ))

failed = []

def noteSkipped(f):
  '''Record the tests that fail.'''
  @functools.wraps(f)
  def skipper(self, modulename):
    try:
      f(self, modulename)
    except:
      failed.append(modulename)
      raise
  return skipper

class TestKiel(cytest.TestCase):
  def setUp(self):
    curry.path.insert(0, SOURCE_DIR)

  @classmethod
  def tearDownClass(cls):
    if failed:
      print 'The following tests failed.  ' \
            'Copy this line into func_kiel.py to skip them.'
    print 'SKIP =', failed

  # Create a test for every file under the source directory.
  for cysrc in glob(SOURCE_DIR + '*.curry'):
    name = os.path.splitext(os.path.split(cysrc)[-1])[0]
    if name not in SKIP:
      locals()['test_'+name] = lambda self, name=name: self.check(name)

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
      cytest.compare.ensureGolden(goldenfile, module, goal, [SOURCE_DIR], '20s')
      my = cytest.compare.cyclean('\n'.join(map(str, curry.eval(goal))+['']))
      self.compareGolden(my, goldenfile)
    self.assertGreater(num, 0)
