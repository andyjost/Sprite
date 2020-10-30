from . import TestCase, oracle
from glob import glob
import curry
import cytest.oracle
import functools
import os
import re
import sys

def noteSkipped(f):
  '''Record the tests that fail.'''
  @functools.wraps(f)
  def skipper(self, modulename):
    try:
      f(self, modulename)
    except:
      self.failed.append(modulename)
      raise
  return skipper


class FunctionalTestCase(TestCase):
  '''
  Base class for functional test case.

  Functional tests check whole program behavior (unlike unit tests, which test
  the smallest units possible).  The input is a directory of .curry files.
  This class runs them and compares the output to an Oracle, such as PAKCS or
  KiCS2.

  Each file produces one test in this class.  All goals matching the specified
  pattern (see below) will be run.  The test passes if every goal matches the
  output of the Oracle.

  The super class specifies the desired behavior by defining the following
  class variables:

      SOURCE_DIR [Required, str]
        The directory to search for .curry files.

      FILE_PATTERN [Optional, str or regex, default=r".*\.curry$"
        The pattern to use use when searching for .curry files.

      GOAL_PATTERN [Optional, str or regex, default=r"(sprite_)?(goal|main)\d*$]"
        The pattern to use when searching for goals.  All functions matching
        this pattern will be run.

      CURRYPATH [Optional, str]
        A colon-delimited list of paths to preprend to the CURRYPATH
        environment variable.  This is needed if the Curry programs use
        non-built-in libraries.  Note that SOURCE_DIR is always added to
        CURRYPATH.

      SKIP [Optional, set, default=set()]
        A list of tests to skip.  Each element can be a string or regular
        expression.  Any .curry file whose base name (i.e., with the .curry
        extension stripped) matches one of these patterns will be skipped.

      ORACLE_TIMEOUT [Optional, int, default=20]
        The timeout in seconds to use when generating golden results.

      PRINT_SKIPPED_FILES [Optional, Bool, default=False]
        Indicates whether to print the names of files that were skipped.

      PRINT_SKIPPED_GOALS [Optional, Bool, default=False]
        Indicates whether to print the names of goals that were skipped.  Only
        goals with arity zero can be run.
  '''
  class __metaclass__(type):
    def __new__(cls, clsname, bases, defs):
      if bases[0] is not TestCase:
        if 'SOURCE_DIR' not in defs:
          raise ValueError('SOURCE_DIR not specified in base class')
        if 'FILE_PATTERN' not in defs:
          defs['FILE_PATTERN'] = r'.*\.curry$'
        defs['FILE_PATTERN'] = re.compile(defs['FILE_PATTERN'])
        if 'GOAL_PATTERN' not in defs:
          defs['GOAL_PATTERN'] = r'(sprite_)?(goal|main)\d*$'
        defs['GOAL_PATTERN'] = re.compile(defs['GOAL_PATTERN'])
        if 'CURRYPATH' not in defs:
          defs['CURRYPATH'] = ''
        defs['CURRYPATH'] = defs['CURRYPATH'].split(':') + [defs['SOURCE_DIR']] + curry.path
        if 'SKIP' not in defs:
          defs['SKIP'] = []
        defs['SKIP'] = re.compile('^$' + '|'.join(defs['SKIP']))
        if 'PRINT_SKIPPED_FILES' not in defs:
          defs['PRINT_SKIPPED_FILES'] = False
        if 'PRINT_SKIPPED_GOALS' not in defs:
          defs['PRINT_SKIPPED_GOALS'] = False

        # Create a test for every file under the source directory.
        for cysrc in glob(defs['SOURCE_DIR'] + '*.curry'):
          if re.match(defs['FILE_PATTERN'], cysrc):
            name = os.path.splitext(os.path.split(cysrc)[-1])[0]
            if re.match(defs['SKIP'], name):
              if defs['PRINT_SKIPPED_FILES']:
                print >>sys.stderr, 'skipping file %s' % cysrc
            else:
              defs['test_' + name] = lambda self, name=name: self.check(name)
      return type.__new__(cls, clsname, bases, defs)

  def setUp(self):
    super(FunctionalTestCase, self).setUp()
    curry.path[:] = self.CURRYPATH

  @classmethod
  def setUpClass(cls):
    super(FunctionalTestCase, cls).setUpClass()
    cls.old_curry_path = curry.path[:]
    cls.failed = []

  @classmethod
  def tearDownClass(cls):
    super(FunctionalTestCase, cls).tearDownClass()
    curry.path[:] = cls.old_curry_path
    if cls.failed:
      print >>sys.stderr, (
          'The following tests failed.  '
          'Copy this line into func_kiel.py to skip them.'
        )
      print >>sys.stderr, 'SKIP =', sorted(cls.failed)

  @oracle.require
  @noteSkipped
  def check(self, modulename):
    '''
    Load the specified module, execute each goal, and compare with goldens
    provided by the oracle.
    '''
    module = curry.import_(modulename)
    goals = [
        v for k,v in module.__dict__.items() if re.match(self.GOAL_PATTERN, k)
      ]
    num_tests_run = 0
    for goal in sorted(goals, key=lambda x: x.ident.basename):
      if goal.info.arity and self.PRINT_SKIPPED_GOALS:
        print >>sys.stderr, 'skipping goal %s because its arity (%s) is not zero' % (
            goal.info.name, goal.info.arity
          )
        continue
      num_tests_run += 1
      goldenfile = os.path.join(self.SOURCE_DIR, goal.ident + '.au-gen')
      oracle.divine(
          module, goal, [self.SOURCE_DIR], '20s', goldenfile=goldenfile
        )
      sprite_result = oracle.cyclean(
          '\n'.join(map(str, curry.eval(goal))+[''])
        )
      self.compareEqualToFile(sprite_result, goldenfile)
    self.assertGreater(num_tests_run, 0)

