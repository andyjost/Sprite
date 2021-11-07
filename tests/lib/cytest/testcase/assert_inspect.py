'''
Assertions based on the curry.inspect module.
'''

from curry import inspect
from curry.context import Node
from curry.backends.py.runtime.graph.equality import (
    logically_equal, structurally_equal
  )

try:
  from curry.llvm import isa as llvm_isa
except ImportError:
  def llvm_isa(*args, **kwds):
    raise RuntimeError('LLVM is not available')

def assertStructEqual(tc, e0, e1):
  '''Compare two Curry expressions for exact structural equality.'''
  tc.assertTrue(structurally_equal(e0, e1))

def assertNotStructEqual(tc, e0, e1):
  tc.assertFalse(structurally_equal(e0, e1))

def assertLogEqual(tc, e0, e1):
  '''Compare two Curry expressions for logical equality.'''
  tc.assertTrue(logically_equal(e0, e1))

def assertNotLogEqual(tc, e0, e1):
  '''Compare two Curry expressions for logical equality.'''
  tc.assertFalse(logically_equal(e0, e1))

def assertNotStructEqual(tc, e0, e1):
  tc.assertFalse(structurally_equal(e0, e1))

def assertIsa(tc, obj, ty):
  isa = inspect.isa if isinstance(obj, Node) else llvm_isa
  tc.assertTrue(isa(obj, ty))

def assertIsNotA(tc, obj, ty):
  isa = inspect.isa if isinstance(obj, Node) else llvm_isa
  tc.assertFalse(isa(obj, ty))

def assertIsaBoxedPrimitive(tc, obj):
  if not inspect.isa_boxed_primitive(obj):
    tc.fail('%r is not a Curry boxed primitive value' % obj)

def assertIsaUnboxedPrimitive(tc, obj):
  if not inspect.isa_unboxed_primitive(obj):
    tc.fail('%r is not a Curry unboxed primitive value' % obj)

def assertIsaCurryExpr(tc, obj):
  if not inspect.isa_curry_expr(obj):
    tc.fail('%r is not a Curry expression' % obj)

def assertIsaPrimitive(tc, obj):
  if not inspect.isa_primitive(obj):
    tc.fail('%r is not a Curry primitive value' % obj)

def assertIsaBoxedInt(tc, obj):
  if not inspect.isa_boxed_int(obj):
    tc.fail('%r is not a Curry boxed integer' % obj)

def assertIsaUnboxedInt(tc, obj):
  if not inspect.isa_unboxed_int(obj):
    tc.fail('%r is not a Curry unboxed integer' % obj)

def assertIsaInt(tc, obj):
  if not inspect.isa_int(obj):
    tc.fail('%r is not a Curry integer' % obj)

def assertIsaBoxedChar(tc, obj):
  if not inspect.isa_boxed_char(obj):
    tc.fail('%r is not a Curry boxed character' % obj)

def assertIsaUnboxedChar(tc, obj):
  if not inspect.isa_unboxed_char(obj):
    tc.fail('%r is not a Curry unboxed character' % obj)

def assertIsaChar(tc, obj):
  if not inspect.isa_char(obj):
    tc.fail('%r is not a Curry character' % obj)

def assertIsaBoxedFloat(tc, obj):
  if not inspect.isa_boxed_float(obj):
    tc.fail('%r is not a Curry boxed floating-point number' % obj)

def assertIsaUnboxedFloat(tc, obj):
  if not inspect.isa_unboxed_float(obj):
    tc.fail('%r is not a Curry unboxed floating-point number' % obj)

def assertIsaFloat(tc, obj):
  if not inspect.isa_float(obj):
    tc.fail('%r is not a Curry floating-point number' % obj)

def assertIsaIO(tc, obj):
  if not inspect.isa_io(obj):
    tc.fail('%r is not a Curry IO' % obj)

def assertIsaBool(tc, obj):
  if not inspect.isa_bool(obj):
    tc.fail('%r is not a Curry Boolean' % obj)

def assertIsaTrue(tc, obj):
  if not inspect.isa_true(obj):
    tc.fail('%r is not a Curry True' % obj)

def assertIsaFalse(tc, obj):
  if not inspect.isa_false(obj):
    tc.fail('%r is not a Curry False' % obj)

def assertIsaList(tc, obj):
  if not inspect.isa_list(obj):
    tc.fail('%r is not a Curry List' % obj)

def assertIsaCons(tc, obj):
  if not inspect.isa_cons(obj):
    tc.fail('%r is not a Curry Cons' % obj)

def assertIsaNil(tc, obj):
  if not inspect.isa_nil(obj):
    tc.fail('%r is not a Curry Nil' % obj)

def assertIsaTuple(tc, obj):
  if not inspect.isa_tuple(obj):
    tc.fail('%r is not a Curry Tuple' % obj)

def assertIsaSetGuard(tc, obj):
  if not inspect.isa_setguard(obj):
    tc.fail('%r is not a Curry set guard' % obj)

def assertIsaFailure(tc, obj):
  if not inspect.isa_failure(obj):
    tc.fail('%r is not a Curry failure' % obj)

def assertIsaConstraint(tc, obj):
  if not inspect.isa_constraint(obj):
    tc.fail('%r is not a Curry constraint' % obj)

def assertIsaFreevar(tc, obj):
  if not inspect.isa_freevar(obj):
    tc.fail('%r is not a Curry free variable' % obj)

def assertIsaFwd(tc, obj):
  if not inspect.isa_fwd(obj):
    tc.fail('%r is not a Curry forward node' % obj)

def assertIsaChoice(tc, obj):
  if not inspect.isa_choice(obj):
    tc.fail('%r is not a Curry choice' % obj)

def assertIsaFunc(tc, obj):
  if not inspect.isa_func(obj):
    tc.fail('%r is not a Curry function' % obj)

def assertIsaCtor(tc, obj):
  if not inspect.isa_ctor(obj):
    tc.fail('%r is not a Curry constructor' % obj)

def assertIsData(tc, obj):
  if not inspect.is_data(obj):
    tc.fail('%r is not Curry data' % obj)

def assertIsBoxed(tc, obj):
  if not inspect.is_boxed(obj):
    tc.fail('%r is not a boxed Curry expression' % obj)

def assertChoiceIdEquals(tc, obj, cid):
  got_id = inspect.get_choice_id(obj)
  if got_id is None:
    tc.fail('%r has no choice ID' % obj)
  else:
    tc.assertEqual(got_id, cid)

def assertVariableIdEquals(tc, obj, vid):
  got_id = inspect.get_variable_id(obj)
  if got_id is None:
    tc.fail('%r has no variable ID' % obj)
  else:
    tc.assertEqual(got_id, vid)

def assertSetIdEquals(tc, obj, sid):
  got_id = inspect.get_set_id(obj)
  if got_id is None:
    tc.fail('%r has no set ID' % obj)
  else:
    tc.assertEqual(got_id, sid)

def assertIsNotABoxedPrimitive(tc, obj):
  if inspect.isa_boxed_primitive(obj):
    tc.fail('%r is a Curry boxed primitive value' % obj)

def assertIsNotAUnboxedPrimitive(tc, obj):
  if inspect.isa_unboxed_primitive(obj):
    tc.fail('%r is a Curry unboxed primitive value' % obj)

def assertIsNotACurryExpr(tc, obj):
  if inspect.isa_curry_expr(obj):
    tc.fail('%r is a Curry expression' % obj)

def assertIsNotAPrimitive(tc, obj):
  if inspect.isa_primitive(obj):
    tc.fail('%r is a Curry primitive value' % obj)

def assertIsNotABoxedInt(tc, obj):
  if inspect.isa_boxed_int(obj):
    tc.fail('%r is a Curry boxed integer' % obj)

def assertIsNotAUnboxedInt(tc, obj):
  if inspect.isa_unboxed_int(obj):
    tc.fail('%r is a Curry unboxed integer' % obj)

def assertIsNotAInt(tc, obj):
  if inspect.isa_int(obj):
    tc.fail('%r is a Curry integer' % obj)

def assertIsNotABoxedChar(tc, obj):
  if inspect.isa_boxed_char(obj):
    tc.fail('%r is a Curry boxed character' % obj)

def assertIsNotAUnboxedChar(tc, obj):
  if inspect.isa_unboxed_char(obj):
    tc.fail('%r is a Curry unboxed character' % obj)

def assertIsNotAChar(tc, obj):
  if inspect.isa_char(obj):
    tc.fail('%r is a Curry character' % obj)

def assertIsNotABoxedFloat(tc, obj):
  if inspect.isa_boxed_float(obj):
    tc.fail('%r is a Curry boxed floating-point number' % obj)

def assertIsNotAUnboxedFloat(tc, obj):
  if inspect.isa_unboxed_float(obj):
    tc.fail('%r is a Curry unboxed floating-point number' % obj)

def assertIsNotAFloat(tc, obj):
  if inspect.isa_float(obj):
    tc.fail('%r is a Curry floating-point number' % obj)

def assertIsNotAIO(tc, obj):
  if inspect.isa_io(obj):
    tc.fail('%r is a Curry IO' % obj)

def assertIsNotABool(tc, obj):
  if inspect.isa_bool(obj):
    tc.fail('%r is a Curry Boolean' % obj)

def assertIsNotATrue(tc, obj):
  if inspect.isa_true(obj):
    tc.fail('%r is a Curry True' % obj)

def assertIsNotAFalse(tc, obj):
  if inspect.isa_false(obj):
    tc.fail('%r is a Curry False' % obj)

def assertIsNotAList(tc, obj):
  if inspect.isa_list(obj):
    tc.fail('%r is a Curry List' % obj)

def assertIsNotACons(tc, obj):
  if inspect.isa_cons(obj):
    tc.fail('%r is a Curry Cons' % obj)

def assertIsNotANil(tc, obj):
  if inspect.isa_nil(obj):
    tc.fail('%r is a Curry Nil' % obj)

def assertIsNotATuple(tc, obj):
  if inspect.isa_tuple(obj):
    tc.fail('%r is a Curry Tuple' % obj)

def assertIsNotASetGuard(tc, obj):
  if inspect.isa_setguard(obj):
    tc.fail('%r is a Curry set guard' % obj)

def assertIsNotAFailure(tc, obj):
  if inspect.isa_failure(obj):
    tc.fail('%r is a Curry failure' % obj)

def assertIsNotAConstraint(tc, obj):
  if inspect.isa_constraint(obj):
    tc.fail('%r is a Curry constraint' % obj)

def assertIsNotAFreevar(tc, obj):
  if inspect.isa_freevar(obj):
    tc.fail('%r is a Curry free variable' % obj)

def assertIsNotAFwd(tc, obj):
  if inspect.isa_fwd(obj):
    tc.fail('%r is a Curry forward node' % obj)

def assertIsNotAChoice(tc, obj):
  if inspect.isa_choice(obj):
    tc.fail('%r is a Curry choice' % obj)

def assertIsNotAFunc(tc, obj):
  if inspect.isa_func(obj):
    tc.fail('%r is a Curry function' % obj)

def assertIsNotACtor(tc, obj):
  if inspect.isa_ctor(obj):
    tc.fail('%r is a Curry constructor' % obj)

def assertIsNotData(tc, obj):
  if inspect.is_data(obj):
    tc.fail('%r is Curry data' % obj)

def assertIsNotBoxed(tc, obj):
  if inspect.is_boxed(obj):
    tc.fail('%r is a boxed Curry expression' % obj)

def assertChoiceIdNotEquals(tc, obj, cid):
  got_id = inspect.get_id(obj)
  if got_id is None:
    tc.fail('%r has no choice ID' % obj)
  else:
    tc.assertNotEqual(got_id, cid)
