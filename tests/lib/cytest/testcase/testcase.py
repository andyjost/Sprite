from cStringIO import StringIO
from curry.context import Node
from curry import inspect as cy_inspect
from curry.llvm import isa as llvm_isa
import collections, curry, gzip, re, sys, unittest
from curry.backends.py.runtime.graph.equality import (
    logically_equal, structurally_equal
  )

__all__ = ['TestCase']

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

  def compareEqualToFile(
      self, objs, filename
    , update=False
    , checker=unittest.TestCase.assertEqual
    ):
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
    ``checker``
        The function called to compare values.
    '''
    if isinstance(objs, str):
      sprite_answer = objs
    else:
      buf = StringIO()
      if isinstance(objs, collections.Sequence):
        for obj in objs: buf.write(str(obj))
      else:
        buf.write(str(objs))
      sprite_answer = buf.getvalue()
    open_ = gzip.open if filename.endswith('.gz') else open
    if update:
      with open_(filename, 'wb') as au:
        au.write(sprite_answer)
    else:
      with open_(filename, 'rb') as au:
        correct_answer = au.read()
      checker(self, sprite_answer, correct_answer)

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

  def assertIsaFreevar(self, obj):
    if not cy_inspect.isa_freevar(obj):
      self.fail('%r is not a Curry free variable' % obj)

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

  def assertIsNotAFreevar(self, obj):
    if cy_inspect.isa_freevar(obj):
      self.fail('%r is a Curry free variable' % obj)

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

  def assertSameResultSet(
      self, sprite_results, oracle_results, check_multiplicity=False
    ):
    from ..readcurry.parse import parse
    from ..readcurry.compare import compare

    # Ensure the results are in a bijection.
    s_count, o_count = (
        collections.Counter(r for r in results.split('\n') if r)
            for results in (sprite_results, oracle_results)
      )

    # Each system should generate the same number of unique answers.
    self.assertEqual(len(s_count), len(o_count))

    # Each answer in one matches an answer in the other.
    s_parsed, o_parsed = (
        {text: parse(text) for text in ab} for ab in (s_count, o_count)
      )
    for s_key, s_val in s_parsed.items():
      # Find a matching key in o_parsed, or fail.
      if s_key in o_parsed:
        o_key = s_key
      else:
        for o_key, o_val in o_parsed.items():
          if compare(s_val, o_val, modulo_variable_renaming=True):
            break
        else:
          self.assertTrue(False, msg='%s not found' % s_val)

      # Check multiplicity, if requested.
      if check_multiplicity:
        self.assertEqual(s_count[s_key], o_count[o_key])

  def assertSameResultMultiset(self, sprite_results, oracle_results):
    self.assertSameResultSet(
        sprite_results, oracle_results, check_multiplicity=True
      )
