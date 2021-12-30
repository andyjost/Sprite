'''
Implements FunctionTestCase.

This is a subclass of unittest.TestCase that automates comparing Sprite's
output that that of another Curry system, called the oracle.  To create a
functional test suite, one creates a subclass that defines the class variable
SOURCE_DIR.  That variable indicates where to search for Curry source files.
Every file discovered is translated into a test_* method of the subclass that
runs the corresponding Curry program.  The output of Sprite compared against
the oracle's output.

The behavior can be fine-tuned by setting additional class variables in the
subclass.  See the documentation for FunctionalTestCase.
'''
from ..clean import clean
from glob import glob
from .. import oracle
from . import testcase
import curry, functools, inspect, os, re, six, sys, unittest

__all__ = ['FunctionalTestCase']

class FunctionalTestCaseMetaclass(type):
  '''
  The metaclass for FunctionalTestCase.  This searches for Curry source files
  and creates the test_* methods.
  '''
  def __new__(cls, clsname, bases, defs):
    if bases[0] is not testcase.TestCase:
      cls.create_testcases(clsname, bases, defs)
    return type.__new__(cls, clsname, bases, defs)

  @classmethod
  def create_testcases(cls, clsname, bases, defs):
    '''
    Defines a test_* method for each .curry file found in the SOURCE_DIR.
    '''
    if 'SOURCE_DIR' not in defs:
      raise ValueError('SOURCE_DIR was not supplied in the base class')
    defs.setdefault('CURRYPATH'          , '')
    defs.setdefault('EXPECTED_FAILURE'   , None)
    defs.setdefault('FILE_PATTERN'       , '[a-z]*.curry')
    defs.setdefault('GOAL_PATTERN'       , r'(sprite_)?(goal|main)\d*$')
    defs.setdefault('PRINT_SKIPPED_FILES', False)
    defs.setdefault('PRINT_SKIPPED_GOALS', True)
    defs.setdefault('RUN_ONLY'           , None)
    defs.setdefault('SKIP'               , None)
    defs.setdefault('CLEAN_KWDS'         , None)
    defs.setdefault('COMPARISON_METHOD'  , None)
    defs.setdefault('CONVERTER'          , None)
    defs.setdefault('DO_CLEAN'           , None)
    defs.setdefault('ORACLE_TIMEOUT'     , None)
    defs['CURRYPATH']         = defs['CURRYPATH'].split(':') + [defs['SOURCE_DIR']] + curry.path
    defs['EXPECTED_FAILURE']  = compile_pattern(defs['EXPECTED_FAILURE'])
    defs['GOAL_PATTERN']      = compile_pattern(defs['GOAL_PATTERN'])
    defs['RUN_ONLY_EXACT']    = compile_pattern(defs['RUN_ONLY'], exact=True)
    defs['RUN_ONLY']          = compile_pattern(defs['RUN_ONLY'])
    defs['SKIP']              = compile_pattern(defs['SKIP'])
    defs['CLEAN_KWDS']        = TSKeywords(defs['CLEAN_KWDS']       , dict, {})
    defs['COMPARISON_METHOD'] = TSKeywords(
        defs['COMPARISON_METHOD'], callable, unittest.TestCase.assertEqual
      )
    defs['CONVERTER']         = TSKeywords(defs['CONVERTER']        , str, None)
    defs['DO_CLEAN']          = TSKeywords(defs['DO_CLEAN']         , bool, True)
    defs['ORACLE_TIMEOUT']    = TSKeywords(defs['ORACLE_TIMEOUT']   , int, 20)

    # Create a test for every file under the source directory.
    for cysrc in glob(defs['SOURCE_DIR'] + defs['FILE_PATTERN']):
      testname = os.path.splitext(os.path.split(cysrc)[-1])[0]
      skipped = defs['SKIP'] and re.match(defs['SKIP'], testname)
      excluded = defs['RUN_ONLY'] and not re.match(defs['RUN_ONLY'], testname)
      forced = defs['RUN_ONLY_EXACT'] and re.match(defs['RUN_ONLY_EXACT'], testname)
      if (skipped and not forced) or excluded:
        if defs['PRINT_SKIPPED_FILES']:
          sys.stderr.write('skipping file %s\n' % cysrc)
      else:
        meth_name = 'test_' + testname
        defs[meth_name] = lambda self, testname=testname: self.check(testname)
        if defs['EXPECTED_FAILURE'] and re.match(defs['EXPECTED_FAILURE'], testname):
          defs[meth_name] = unittest.expectedFailure(defs[meth_name])



class FunctionalTestCase(
    six.with_metaclass(FunctionalTestCaseMetaclass, testcase.TestCase)
  ):
  '''
  Base class for functional test cases.

  Functional tests check whole program behavior (unlike unit tests, which test
  bits and pieces).  The input is a directory of .curry files.  This class runs
  them and compares the output to an Oracle, such as PAKCS or KiCS2.

  Each file produces one test in this class.  All goals matching the specified
  pattern (see below) will be run.  The test passes if every goal matches the
  output of the Oracle.

  Subclasses are required to define the following class variable:

      SOURCE_DIR [Required, str]
        The directory to search for .curry files.

  The following optional class variables can be used to fine-tune the behavior
  for all tests:

      CURRYPATH [Optional, str]
        A colon-delimited list of paths to preprend to the CURRYPATH
        environment variable.  This is needed if the Curry programs use
        non-built-in libraries.  SOURCE_DIR is always added to CURRYPATH.

      FILE_PATTERN [Optional, str (glob), default="[a-z]*.curry"
        The pattern to use use when searching for Curry source files.

      GOAL_PATTERN [Optional, str (regex), default=r"(sprite_)?(goal|main)\d*$]"
        The pattern to use when searching for goals.  All functions matching
        this pattern will be run.

      PRINT_SKIPPED_FILES [Optional, Bool, default=False]
        Indicates whether to print the names of files that were skipped.

      PRINT_SKIPPED_GOALS [Optional, Bool, default=True]
        Indicates whether to print the names of goals that were skipped.  Only
        goals with arity zero can be run.

      RUN_ONLY [Optional, set or str, default=None]
        The opposite of SKIP.  Specifies the tests to run.  If RUN_ONLY and
        SKIP both apply to a test, then the test is run only if the RUN_ONLY
        pattern exactly matches the test name.

      SKIP [Optional, set or str, default=None]
        A list of tests to skip.  Each element is interpreted as a regular
        expression.  Any .curry file whose base name (i.e., with the .curry
        extension stripped) matches one of these patterns will be skipped.

  The following variables can be used to fine-tune the behavior of individual
  tests.  If a value is supplied, it applies to all tests.  If a mapping from
  strings to values is supplied, then a value applies only if the corresponding
  string matches the test name.

      CLEAN_KWDS [Optional, dict or {str:dict}]
        File-specific options to clean.clean.  For tests matching the key, the
        provided keywords will be passed to the cleanup function.  If any value
        is a dict, then it is assumed the dict contains test-specific keyword
        dicts.

      COMPARISON_METHOD [Optional, callable or {str:callable}, assertEqual]
        Specifies the method used to compare results.

      CONVERTER [Optional, str or {str:str}, default=None]
        Specifies the 'defaultconverter' flag.  This controls how Curry values are
        converted to Python before being output by the REPL.

      DO_CLEAN [Optional, bool or {str:bool}, default=False]
        Indicates whether to perform the cleanup step by calling
        ``clean.clean``.  This is a string-to-string transformation applied to
        both the output of Sprite and the oracle.

      ORACLE_TIMEOUT [Optional, int or {str:int}, default=20]
        The timeout in seconds to use when generating golden results.

  '''
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
      sys.stderr.write(
          'The tests listed below failed.  Update %r to skip them.\n'
              % inspect.getfile(cls)
        )
      sys.stderr.write('SKIP = %s\n' % sorted(cls.failed))

  def __collectFailures(f):
    '''Record the tests that fail and print them at the end.'''
    @functools.wraps(f)
    def wrapper(self, testname, *args, **kwds):
      try:
        f(self, testname, *args, **kwds)
      except:
        self.failed.append(testname)
        raise
    return wrapper

  @oracle.require
  @__collectFailures
  def check(self, testname):
    '''
    Load the specified module, execute each goal, and compare with goldens
    provided by the oracle.
    '''
    curry.flags['defaultconverter'] = self.CONVERTER[testname]
    module = curry.import_(testname)
    goals = [v for k,v in module.__dict__.items() if re.match(self.GOAL_PATTERN, k)]
    num_tests_run = 0
    failures = []
    for goal in sorted(goals, key=lambda x: x.name):
      if goal.info.arity and self.PRINT_SKIPPED_GOALS:
        sys.stderr.write(
            'skipping goal %s because its arity (%s) is not zero\n' % (
                goal.info.name, goal.info.arity
              )
          )
        continue
      num_tests_run += 1
      goldenfile = os.path.join(self.SOURCE_DIR, goal.fullname + '.au-gen')
      oracle.divine(module, goal, [self.SOURCE_DIR], '20s', goldenfile=goldenfile)

      with open(goldenfile) as istream:
        oracle_answer_raw = istream.read()

      try:
        results = list(self.evaluate(testname, module, goal))
      except curry.EvaluationSuspended:
        if oracle_answer_raw != '!suspend':
          failures.append('\n====== %r ======\n%s'
              % (goal.name, 'evaluation suspended unexpectedly')
              )
        continue
      else:
        if oracle_answer_raw == '!suspend':
          failures.append('\n====== %r ======\n%s'
              % (goal.name, 'evaluation did not suspend as expected')
              )
          continue

      sprite_answer_raw = '\n'.join([curry.show_value(x) for x in results])
      sprite_answer_raw += '\n'

      if self.DO_CLEAN[testname]:
        oracle_answer = clean(oracle_answer_raw, **self.CLEAN_KWDS[testname])
        sprite_answer = clean(sprite_answer_raw, **self.CLEAN_KWDS[testname])
      else:
        oracle_answer = oracle_answer_raw
        sprite_answer = sprite_answer_raw

      compare = self.COMPARISON_METHOD[testname]
      try:
        compare(self, sprite_answer, oracle_answer)
      except BaseException as exc:
        failures.append('\n====== %r ======\n%s' % (goal.name, exc))

    self.assertGreater(num_tests_run, 0)
    if failures:
      self.fail('the following tests failed:\n%s' % '\n\n'.join(failures))

  def evaluate(self, testname, module, goal):
    '''
    Evaluates a Curry expression under Sprite.  Subclasses may override this to
    control evaluation.
    '''
    return curry.eval(goal)


def compile_pattern(arg, exact=False):
  '''
  Compiles a string or list of strings into a regex.  When a list of strings is
  provided, they are joined with |.
  '''
  if arg is not None:
    if isinstance(arg, six.string_types):
      arg = [arg]
    if exact:
      arg = ['^%s$' % re.escape(a) for a in arg]
    return re.compile('|'.join(arg))

class TSKeywords(object):
  '''
  Test-specific keywords.  Subclasses may specify a single override value, or a
  dict of {pattern: value} to control the behavior on a case-by-case basis.
  '''
  def __init__(self, supplied, value_type, default):
    '''
    The supplied value may be None, a value, or a mapping from strings to
    values.  This object keeps a set of special cases and default if none
    match.  If the supplied argument is a value applicable to all tests,
    then it is implemented by storing that as the default.
    '''
    # The mapping must have the correct element types.  This is needed for
    # CLEAN_KWDS, whose mapping form is {str: dict}.  If a {str: str} is
    # provided, that would be a single value -- a set of keyword arguments --
    # that applies to all tests.
    is_map = isinstance(supplied, dict) and all(
        isinstance(k, six.string_types) and isinstance(v, value_type)
            for k,v in supplied.items()
      )
    if is_map:
      self.cases = {compile_pattern(k): v for k,v in supplied.items()}
      self.default = default
    else:
      self.cases = {}
      self.default = default if supplied is None else supplied

  def __getitem__(self, testname):
    for pattern, value in self.cases.items():
      if re.match(pattern, testname):
        return value
    else:
      return self.default

