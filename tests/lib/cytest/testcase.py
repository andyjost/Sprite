from cStringIO import StringIO
from curry import inspect as cy_inspect
from curry.context import Node
from curry.llvm import isa as llvm_isa
from glob import glob
from . import oracle
import collections
import curry
import functools
import gzip
import inspect
import os
import re
import sys
import unittest
from curry.backends.py.runtime.graph.equality import (
    logically_equal, structurally_equal
  )

class TestCase(unittest.TestCase):
  '''A base test case class for testing Sprite.'''
  def tearDown(self):
    curry.reset() # Undo, e.g., path and I/O modifications after each test.

  # New in Python 3.4.
  if not hasattr(unittest.TestCase, 'assertRegex'):
    def assertRegex(self, string, pattern):
      string, pattern = str(string), str(pattern)
      self.assertTrue(
          re.search(pattern, string)
        , msg='%r does not match pattern %r' % (string, pattern)
        )

  def compareEqualToFile(self, objs, filename, update=False):
    '''
    Compare an object or objects against a golden file.

    Parameters:
    -----------
    ``objs``
        An object or sequence of objects to compare.
    ``filename``
        The name of the file that stores the golden result.
    ``update``
        If true, then just update the golden file.
    '''
    if isinstance(objs, str):
      value = objs
    else:
      buf = StringIO()
      if isinstance(objs, collections.Sequence):
        for obj in objs: buf.write(str(obj))
      else:
        buf.write(str(objs))
      value = buf.getvalue()
    open_ = gzip.open if filename.endswith('.gz') else open
    if update:
      with open_(filename, 'wb') as au:
        au.write(value)
    else:
      with open_(filename, 'rb') as au:
        text = au.read()
      self.assertEqual(value, text)

  def assertStructEqual(self, e0, e1):
    '''Compare two Curry expressions for exact structural equality.'''
    self.assertTrue(structurally_equal(e0, e1))

  def assertNotStructEqual(self, e0, e1):
    self.assertFalse(structurally_equal(e0, e1))

  def assertLogEqual(self, e0, e1):
    '''Compare two Curry expressions for logical equality.'''
    self.assertTrue(logically_equal(e0, e1))

  def assertNotLogEqual(self, e0, e1):
    '''Compare two Curry expressions for logical equality.'''
    self.assertFalse(logically_equal(e0, e1))

  def assertNotStructEqual(self, e0, e1):
    self.assertFalse(structurally_equal(e0, e1))

  def assertIsa(self, obj, ty):
    isa = cy_inspect.isa if isinstance(obj, Node) else llvm_isa
    self.assertTrue(isa(obj, ty))

  def assertIsNotA(self, obj, ty):
    isa = cy_inspect.isa if isinstance(obj, Node) else llvm_isa
    self.assertFalse(isa(obj, ty))

  def assertIsaBoxedPrimitive(self, obj):
    if not cy_inspect.isa_boxed_primitive(obj):
      self.fail('%r is not a Curry boxed primitive value' % obj)

  def assertIsaUnboxedPrimitive(self, obj):
    if not cy_inspect.isa_unboxed_primitive(obj):
      self.fail('%r is not a Curry unboxed primitive value' % obj)

  def assertIsaCurryExpr(self, obj):
    if not cy_inspect.isa_curry_expr(obj):
      self.fail('%r is not a Curry expression' % obj)

  def assertIsaPrimitive(self, obj):
    if not cy_inspect.isa_primitive(obj):
      self.fail('%r is not a Curry primitive value' % obj)

  def assertIsaBoxedInt(self, obj):
    if not cy_inspect.isa_boxed_int(obj):
      self.fail('%r is not a Curry boxed integer' % obj)

  def assertIsaUnboxedInt(self, obj):
    if not cy_inspect.isa_unboxed_int(obj):
      self.fail('%r is not a Curry unboxed integer' % obj)

  def assertIsaInt(self, obj):
    if not cy_inspect.isa_int(obj):
      self.fail('%r is not a Curry integer' % obj)

  def assertIsaBoxedChar(self, obj):
    if not cy_inspect.isa_boxed_char(obj):
      self.fail('%r is not a Curry boxed character' % obj)

  def assertIsaUnboxedChar(self, obj):
    if not cy_inspect.isa_unboxed_char(obj):
      self.fail('%r is not a Curry unboxed character' % obj)

  def assertIsaChar(self, obj):
    if not cy_inspect.isa_char(obj):
      self.fail('%r is not a Curry character' % obj)

  def assertIsaBoxedFloat(self, obj):
    if not cy_inspect.isa_boxed_float(obj):
      self.fail('%r is not a Curry boxed floating-point number' % obj)

  def assertIsaUnboxedFloat(self, obj):
    if not cy_inspect.isa_unboxed_float(obj):
      self.fail('%r is not a Curry unboxed floating-point number' % obj)

  def assertIsaFloat(self, obj):
    if not cy_inspect.isa_float(obj):
      self.fail('%r is not a Curry floating-point number' % obj)

  def assertIsaIO(self, obj):
    if not cy_inspect.isa_io(obj):
      self.fail('%r is not a Curry IO' % obj)

  def assertIsaBool(self, obj):
    if not cy_inspect.isa_bool(obj):
      self.fail('%r is not a Curry Boolean' % obj)

  def assertIsaTrue(self, obj):
    if not cy_inspect.isa_true(obj):
      self.fail('%r is not a Curry True' % obj)

  def assertIsaFalse(self, obj):
    if not cy_inspect.isa_false(obj):
      self.fail('%r is not a Curry False' % obj)

  def assertIsaList(self, obj):
    if not cy_inspect.isa_list(obj):
      self.fail('%r is not a Curry List' % obj)

  def assertIsaCons(self, obj):
    if not cy_inspect.isa_cons(obj):
      self.fail('%r is not a Curry Cons' % obj)

  def assertIsaNil(self, obj):
    if not cy_inspect.isa_nil(obj):
      self.fail('%r is not a Curry Nil' % obj)

  def assertIsaTuple(self, obj):
    if not cy_inspect.isa_tuple(obj):
      self.fail('%r is not a Curry Tuple' % obj)

  def assertIsaSetGuard(self, obj):
    if not cy_inspect.isa_setguard(obj):
      self.fail('%r is not a Curry set guard' % obj)

  def assertIsaFailure(self, obj):
    if not cy_inspect.isa_failure(obj):
      self.fail('%r is not a Curry failure' % obj)

  def assertIsaConstraint(self, obj):
    if not cy_inspect.isa_constraint(obj):
      self.fail('%r is not a Curry constraint' % obj)

  def assertIsaVariable(self, obj):
    if not cy_inspect.isa_variable(obj):
      self.fail('%r is not a Curry variable' % obj)

  def assertIsaFwd(self, obj):
    if not cy_inspect.isa_fwd(obj):
      self.fail('%r is not a Curry forward node' % obj)

  def assertIsaChoice(self, obj):
    if not cy_inspect.isa_choice(obj):
      self.fail('%r is not a Curry choice' % obj)

  def assertIsaFunc(self, obj):
    if not cy_inspect.isa_func(obj):
      self.fail('%r is not a Curry function' % obj)

  def assertIsaCtor(self, obj):
    if not cy_inspect.isa_ctor(obj):
      self.fail('%r is not a Curry constructor' % obj)

  def assertIsData(self, obj):
    if not cy_inspect.is_data(obj):
      self.fail('%r is not Curry data' % obj)

  def assertIsBoxed(self, obj):
    if not cy_inspect.is_boxed(obj):
      self.fail('%r is not a boxed Curry expression' % obj)

  def assertChoiceIdEquals(self, obj, cid):
    got_id = cy_inspect.get_choice_id(obj)
    if got_id is None:
      self.fail('%r has no choice ID' % obj)
    else:
      self.assertEqual(got_id, cid)

  def assertVariableIdEquals(self, obj, vid):
    got_id = cy_inspect.get_variable_id(obj)
    if got_id is None:
      self.fail('%r has no variable ID' % obj)
    else:
      self.assertEqual(got_id, vid)

  def assertSetIdEquals(self, obj, sid):
    got_id = cy_inspect.get_set_id(obj)
    if got_id is None:
      self.fail('%r has no set ID' % obj)
    else:
      self.assertEqual(got_id, sid)

  def assertIsNotABoxedPrimitive(self, obj):
    if cy_inspect.isa_boxed_primitive(obj):
      self.fail('%r is a Curry boxed primitive value' % obj)

  def assertIsNotAUnboxedPrimitive(self, obj):
    if cy_inspect.isa_unboxed_primitive(obj):
      self.fail('%r is a Curry unboxed primitive value' % obj)

  def assertIsNotACurryExpr(self, obj):
    if cy_inspect.isa_curry_expr(obj):
      self.fail('%r is a Curry expression' % obj)

  def assertIsNotAPrimitive(self, obj):
    if cy_inspect.isa_primitive(obj):
      self.fail('%r is a Curry primitive value' % obj)

  def assertIsNotABoxedInt(self, obj):
    if cy_inspect.isa_boxed_int(obj):
      self.fail('%r is a Curry boxed integer' % obj)

  def assertIsNotAUnboxedInt(self, obj):
    if cy_inspect.isa_unboxed_int(obj):
      self.fail('%r is a Curry unboxed integer' % obj)

  def assertIsNotAInt(self, obj):
    if cy_inspect.isa_int(obj):
      self.fail('%r is a Curry integer' % obj)

  def assertIsNotABoxedChar(self, obj):
    if cy_inspect.isa_boxed_char(obj):
      self.fail('%r is a Curry boxed character' % obj)

  def assertIsNotAUnboxedChar(self, obj):
    if cy_inspect.isa_unboxed_char(obj):
      self.fail('%r is a Curry unboxed character' % obj)

  def assertIsNotAChar(self, obj):
    if cy_inspect.isa_char(obj):
      self.fail('%r is a Curry character' % obj)

  def assertIsNotABoxedFloat(self, obj):
    if cy_inspect.isa_boxed_float(obj):
      self.fail('%r is a Curry boxed floating-point number' % obj)

  def assertIsNotAUnboxedFloat(self, obj):
    if cy_inspect.isa_unboxed_float(obj):
      self.fail('%r is a Curry unboxed floating-point number' % obj)

  def assertIsNotAFloat(self, obj):
    if cy_inspect.isa_float(obj):
      self.fail('%r is a Curry floating-point number' % obj)

  def assertIsNotAIO(self, obj):
    if cy_inspect.isa_io(obj):
      self.fail('%r is a Curry IO' % obj)

  def assertIsNotABool(self, obj):
    if cy_inspect.isa_bool(obj):
      self.fail('%r is a Curry Boolean' % obj)

  def assertIsNotATrue(self, obj):
    if cy_inspect.isa_true(obj):
      self.fail('%r is a Curry True' % obj)

  def assertIsNotAFalse(self, obj):
    if cy_inspect.isa_false(obj):
      self.fail('%r is a Curry False' % obj)

  def assertIsNotAList(self, obj):
    if cy_inspect.isa_list(obj):
      self.fail('%r is a Curry List' % obj)

  def assertIsNotACons(self, obj):
    if cy_inspect.isa_cons(obj):
      self.fail('%r is a Curry Cons' % obj)

  def assertIsNotANil(self, obj):
    if cy_inspect.isa_nil(obj):
      self.fail('%r is a Curry Nil' % obj)

  def assertIsNotATuple(self, obj):
    if cy_inspect.isa_tuple(obj):
      self.fail('%r is a Curry Tuple' % obj)

  def assertIsNotASetGuard(self, obj):
    if cy_inspect.isa_setguard(obj):
      self.fail('%r is a Curry set guard' % obj)

  def assertIsNotAFailure(self, obj):
    if cy_inspect.isa_failure(obj):
      self.fail('%r is a Curry failure' % obj)

  def assertIsNotAConstraint(self, obj):
    if cy_inspect.isa_constraint(obj):
      self.fail('%r is a Curry constraint' % obj)

  def assertIsNotAVariable(self, obj):
    if cy_inspect.isa_variable(obj):
      self.fail('%r is a Curry variable' % obj)

  def assertIsNotAFwd(self, obj):
    if cy_inspect.isa_fwd(obj):
      self.fail('%r is a Curry forward node' % obj)

  def assertIsNotAChoice(self, obj):
    if cy_inspect.isa_choice(obj):
      self.fail('%r is a Curry choice' % obj)

  def assertIsNotAFunc(self, obj):
    if cy_inspect.isa_func(obj):
      self.fail('%r is a Curry function' % obj)

  def assertIsNotACtor(self, obj):
    if cy_inspect.isa_ctor(obj):
      self.fail('%r is a Curry constructor' % obj)

  def assertIsNotData(self, obj):
    if cy_inspect.is_data(obj):
      self.fail('%r is Curry data' % obj)

  def assertIsNotBoxed(self, obj):
    if cy_inspect.is_boxed(obj):
      self.fail('%r is a boxed Curry expression' % obj)

  def assertChoiceIdNotEquals(self, obj, cid):
    got_id = cy_inspect.get_id(obj)
    if got_id is None:
      self.fail('%r has no choice ID' % obj)
    else:
      self.assertNotEqual(got_id, cid)

  def assertMayRaise(self, exception, expr, msg=None):
    if exception is None:
      try:
        expr()
      except:
        info = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        self.fail('%s raised%s' % (repr(info[0]), tail))
    else:
      try:
        self.assertRaises(exception, expr)
      except:
        ty,val,tb = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        raise ty, ty(str(val) + tail), tb

  def assertMayRaiseRegexp(self, exception, regexp, expr, msg=None):
    if exception is None:
      try:
        expr()
      except:
        info = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        self.fail('%s raised%s' % (repr(info[0]), tail))
    else:
      try:
        self.assertRaisesRegexp(exception, regexp, expr)
      except:
        ty,val,tb = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        raise ty, ty(str(val) + tail), tb


def noteSkipped(f):
  '''Record the tests that fail.'''
  @functools.wraps(f)
  def skipper(self, modulename, *args, **kwds):
    try:
      f(self, modulename, *args, **kwds)
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

      FILE_PATTERN [Optional, str (glob), default=r"*.curry"
        The pattern to use use when searching for Curry source files.

      GOAL_PATTERN [Optional, str (regex), default=r"(sprite_)?(goal|main)\d*$]"
        The pattern to use when searching for goals.  All functions matching
        this pattern will be run.

      CURRYPATH [Optional, str]
        A colon-delimited list of paths to preprend to the CURRYPATH
        environment variable.  This is needed if the Curry programs use
        non-built-in libraries.  Note that SOURCE_DIR is always added to
        CURRYPATH.

      CONVERTER [Optional, str, None]
        Specifies the 'defaultconverter' flag.

      CLEAN_KWDS [Optional, {str:dict}]
        File-specific options to cyclean.  For tests matching the key, the
        provided keywords will be passed to cyclean.

      SKIP [Optional, set or str, default=set()]
        A list of tests to skip.  Each element is interpreted as a regular
        expression.  Any .curry file whose base name (i.e., with the .curry
        extension stripped) matches one of these patterns will be skipped.

      RUN_ONLY [Optional, set or str, default='.*']
        The opposite of SKIP.  Specifies the tests to run.

      ORACLE_TIMEOUT [Optional, int, default=20]
        The timeout in seconds to use when generating golden results.

      PRINT_SKIPPED_FILES [Optional, Bool, default=False]
        Indicates whether to print the names of files that were skipped.

      PRINT_SKIPPED_GOALS [Optional, Bool, default=True]
        Indicates whether to print the names of goals that were skipped.  Only
        goals with arity zero can be run.
  '''
  class __metaclass__(type):
    def __new__(cls, clsname, bases, defs):
      if bases[0] is not TestCase:
        if 'SOURCE_DIR' not in defs:
          raise ValueError('SOURCE_DIR not specified in base class')
        if 'FILE_PATTERN' not in defs:
          defs['FILE_PATTERN'] = '*.curry'
        if 'GOAL_PATTERN' not in defs:
          defs['GOAL_PATTERN'] = r'(sprite_)?(goal|main)\d*$'
        defs['GOAL_PATTERN'] = re.compile(defs['GOAL_PATTERN'])
        if 'CURRYPATH' not in defs:
          defs['CURRYPATH'] = ''
        defs['CURRYPATH'] = defs['CURRYPATH'].split(':') + [defs['SOURCE_DIR']] + curry.path
        if 'CLEAN_KWDS' not in defs:
          defs['CLEAN_KWDS'] = {}
        if 'SKIP' not in defs:
          defs['SKIP'] = None
        else:
          skiparg = defs['SKIP']
          if isinstance(skiparg, basestring):
            skiparg = [skiparg]
          defs['SKIP'] = re.compile('|'.join(skiparg))
        if 'RUN_ONLY' not in defs:
          defs['RUN_ONLY'] = None
        else:
          runonlyarg = defs['RUN_ONLY']
          if isinstance(runonlyarg, basestring):
            runonlyarg = [runonlyarg]
          defs['RUN_ONLY'] = re.compile('|'.join(runonlyarg))
        if 'PRINT_SKIPPED_FILES' not in defs:
          defs['PRINT_SKIPPED_FILES'] = False
        if 'PRINT_SKIPPED_GOALS' not in defs:
          defs['PRINT_SKIPPED_GOALS'] = True

        # Create a test for every file under the source directory.
        for cysrc in glob(defs['SOURCE_DIR'] + defs['FILE_PATTERN']):
          name = os.path.splitext(os.path.split(cysrc)[-1])[0]
          if defs['SKIP'] and re.match(defs['SKIP'], name) or \
             defs['RUN_ONLY'] and not re.match(defs['RUN_ONLY'], name):
            if defs['PRINT_SKIPPED_FILES']:
              print >>sys.stderr, 'skipping file %s' % cysrc
          else:
            clean_kwds = defs['CLEAN_KWDS'].get(name, {})
            converter = defs.get('CONVERTER', None)
            test_name = 'test_' + name
            defs[test_name] = cls._make_test(name, clean_kwds, converter)

      return type.__new__(cls, clsname, bases, defs)

    @staticmethod
    def _make_test(name, clean_kwds, converter):
      def test(self):
        if converter:
          curry.flags['defaultconverter'] = converter
        self.check(name, clean_kwds)
      return test

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
          'The tests listed below failed.  Update %r to skip them.'
              % inspect.getfile(cls)
        )
      print >>sys.stderr, 'SKIP =', sorted(cls.failed)

  @oracle.require
  @noteSkipped
  def check(self, modulename, clean_kwds):
    '''
    Load the specified module, execute each goal, and compare with goldens
    provided by the oracle.
    '''
    module = curry.import_(modulename)
    goals = [
        v for k,v in module.__dict__.items() if re.match(self.GOAL_PATTERN, k)
      ]
    num_tests_run = 0
    for goal in sorted(goals, key=lambda x: x.name):
      if goal.info.arity and self.PRINT_SKIPPED_GOALS:
        print >>sys.stderr, 'skipping goal %s because its arity (%s) is not zero' % (
            goal.info.name, goal.info.arity
          )
        continue
      num_tests_run += 1
      goldenfile = os.path.join(self.SOURCE_DIR, goal.fullname + '.au-gen')
      oracle.divine(
          module, goal, [self.SOURCE_DIR], '20s', goldenfile=goldenfile
        , clean_kwds=clean_kwds
        )
      sprite_result = oracle.cyclean(
          '\n'.join(map(curry.show_value, curry.eval(goal))+[''])
        , **clean_kwds
        )
      self.compareEqualToFile(sprite_result, goldenfile)
    self.assertGreater(num_tests_run, 0)

