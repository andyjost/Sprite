'''
Tests for the search programs split by hand under data/curry/benchmarks/
split, the inputs of the split suite of the benchmark harness (see
tests/README, section 9).  Each module spells the whole program and its
parts as functions of the size, so the partition can be checked at a small
size: the parts of a split together generate every permutation once, and
their solutions are those of the original program.
'''
import cytest # from ./lib; must be first
import collections, curry, math, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')
SPLITDIR = os.path.join(BENCHMARKS, 'split')
CURRYPATH = [SPLITDIR, BENCHMARKS] + curry.path
PARTS = (2, 4, 8)
# The sizes of the checks.  The permutations are n! in number.  The Python
# backend narrows slowly, so it checks the solutions at a smaller size.
PERMS_SIZE = 5
SOLUTIONS_SIZE = 6 if curry.flags['backend'] == 'cxx' else 5
# The split module of each program, and the function of the original
# program that takes the size.
PROGRAMS = (
    ('PermSort', 'sortmain'), ('SearchQueens', 'queens')
  , ('QueensSet', 'queens')
  )


class TestSplitPrograms(cytest.TestCase):
  '''The parts of every split partition the search space.'''

  def values(self, *goal):
    return collections.Counter(
        tuple(v) for v in curry.eval(*goal, converter='topython')
      )

  def check(self, program, function):
    M = curry.import_(program + 'Split', currypath=CURRYPATH)
    O = curry.import_(program, currypath=CURRYPATH)
    # The permutations: n! distinct ones; every part generates its share
    # and no permutation twice; every part of a split into at most n parts
    # has some.
    perms = self.values(M.perms, PERMS_SIZE)
    self.assertEqual(sum(perms.values()), math.factorial(PERMS_SIZE))
    self.assertEqual(max(perms.values()), 1)
    for k in PARTS:
      parts = [
          self.values(M.permsPart, PERMS_SIZE, k, i) for i in range(k)
        ]
      self.assertEqual(sum(parts, collections.Counter()), perms, k)
      if k <= PERMS_SIZE:
        self.assertTrue(all(parts), k)
    # The solutions: those of the original program and of the whole.
    whole = self.values(M.whole, SOLUTIONS_SIZE)
    self.assertGreater(len(whole), 0)
    self.assertEqual(whole, self.values(getattr(O, function), SOLUTIONS_SIZE))
    for k in PARTS:
      parts = collections.Counter()
      for i in range(k):
        parts.update(self.values(M.part, SOLUTIONS_SIZE, k, i))
      self.assertEqual(parts, whole, k)

  def test_permsort(self):
    self.check(*PROGRAMS[0])

  def test_searchqueens(self):
    self.check(*PROGRAMS[1])

  def test_queensset(self):
    self.check(*PROGRAMS[2])

  def test_goals(self):
    '''Every module spells main and the goals of the parts.'''
    for program, _ in PROGRAMS:
      M = curry.import_(program + 'Split', currypath=CURRYPATH)
      for name in ['main'] + [
          'part%d_%d' % (k, i) for k in PARTS for i in range(k)
        ]:
        self.assertTrue(hasattr(M, name), (program, name))
