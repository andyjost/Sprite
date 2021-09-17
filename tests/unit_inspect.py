import cytest # from ./lib; must be first
import cytest.expression_library
import curry
from curry import inspect
from curry.expressions import unboxed, var

class TestInspect(cytest.expression_library.ExpressionLibTestCase):
  def testIsaTypeError(self):
    self.assertIsa(curry.expr(1), curry.symbol('Prelude.Int'))
    self.assertRaisesRegexp(
        TypeError
      , 'arg 2 must be an instance or sequence of curry.objects.CurryNodeLabel objects.'
      , lambda: inspect.isa(curry.expr(1), self.not_a_node)
      )

  def testIsaCurryExpr(self):
    map(self.assertIsaCurryExpr, self.everything - set([self.not_a_node]))

  def testIsaPrimitive(self):
    boxed_primitives = [self.int, self.char, self.float]
    unboxed_primitives = [self.unboxed_int, self.unboxed_char, self.unboxed_float]
    primitives = boxed_primitives + unboxed_primitives
    map(self.assertIsaPrimitive, primitives)
    map(self.assertIsaBoxedPrimitive, boxed_primitives)
    map(self.assertIsaUnboxedPrimitive, unboxed_primitives)
    map(self.assertIsNotAPrimitive, self.everything - set(primitives))
    map(self.assertIsNotABoxedPrimitive, self.everything - set(boxed_primitives))
    map(self.assertIsNotAUnboxedPrimitive, self.everything - set(unboxed_primitives))

    # Tests for is_boxed
    not_boxed = unboxed_primitives + [self.not_a_node]
    map(self.assertIsBoxed, self.everything - set(not_boxed))
    map(self.assertIsNotBoxed, not_boxed)

  def testIsaInt(self):
    map(self.assertIsaInt, [self.int, self.unboxed_int])
    self.assertIsaBoxedInt(self.int)
    self.assertIsaUnboxedInt(self.unboxed_int)
    map(self.assertIsNotAInt, self.everything - set([self.int, self.unboxed_int]))
    map(self.assertIsNotABoxedInt, self.everything - set([self.int]))
    map(self.assertIsNotAUnboxedInt, self.everything - set([self.unboxed_int]))

  def testIsaChar(self):
    map(self.assertIsaChar, [self.char, self.unboxed_char])
    self.assertIsaBoxedChar(self.char)
    self.assertIsaUnboxedChar(self.unboxed_char)
    map(self.assertIsNotAChar, self.everything - set([self.char, self.unboxed_char]))
    map(self.assertIsNotABoxedChar, self.everything - set([self.char]))
    map(self.assertIsNotAUnboxedChar, self.everything - set([self.unboxed_char]))

  def testIsaFloat(self):
    map(self.assertIsaFloat, [self.float, self.unboxed_float])
    self.assertIsaBoxedFloat(self.float)
    self.assertIsaUnboxedFloat(self.unboxed_float)
    map(self.assertIsNotAFloat, self.everything - set([self.float, self.unboxed_float]))
    map(self.assertIsNotABoxedFloat, self.everything - set([self.float]))
    map(self.assertIsNotAUnboxedFloat, self.everything - set([self.unboxed_float]))

  def testIsaIO(self):
    self.assertIsaIO(self.io)
    map(self.assertIsNotAIO, self.everything - set([self.io]))

  def testIsaBool(self):
    self.assertIsaTrue(self.true)
    self.assertIsaFalse(self.false)
    map(self.assertIsaBool, [self.true, self.false])
    map(self.assertIsNotATrue, self.everything - set([self.true]))
    map(self.assertIsNotAFalse, self.everything - set([self.false]))
    map(self.assertIsNotABool, self.everything - set([self.true, self.false]))

  def testIsaList(self):
    nonempty_lists = [self.list, self.string]
    empty_lists = [self.empty_list, self.empty_string]
    lists = nonempty_lists + empty_lists
    map(self.assertIsaCons, nonempty_lists)
    map(self.assertIsaNil, empty_lists)
    map(self.assertIsaList, lists)
    map(self.assertIsNotACons, self.everything - set(nonempty_lists))
    map(self.assertIsNotANil, self.everything - set(empty_lists))
    map(self.assertIsNotAList, self.everything - set(lists))

  def testIsaTuple(self):
    self.assertIsaTuple(self.tuple)
    map(self.assertIsNotATuple, self.everything - set([self.tuple]))

    for good in ['()', '(,)', '(,,)', '(,,,,,,,,)']:
      self.assertTrue(inspect.isa_tuple_name(good))
    for bad in ['', '(', '(,', ',,,,,,,,)', ',', ',,,', ')']:
      self.assertFalse(inspect.isa_tuple_name(bad))

  def testIsaSetGuard(self):
    self.assertIsaSetGuard(self.setgrd)
    map(self.assertIsNotASetGuard, self.everything - set([self.setgrd]))

  def testIsaFailure(self):
    self.assertIsaFailure(self.failure)
    map(self.assertIsNotAFailure, self.everything - set([self.failure]))

  def testIsaConstraint(self):
    constraints = [self.nonstrict_constraint, self.strict_constraint, self.value_binding]
    map(self.assertIsaConstraint, constraints)
    map(self.assertIsNotAConstraint, self.everything - set(constraints))

  def testIsaVariable(self):
    self.assertIsaFreevar(self.var)
    map(self.assertIsNotAFreevar, self.everything - set([self.var]))

  def testIsaFwd(self):
    self.assertIsaFwd(self.fwd)
    map(self.assertIsNotAFwd, self.everything - set([self.fwd]))

    # Tests for fwd_target.
    self.assertEqual(inspect.fwd_target(self.fwd), self.true)
    self.assertTrue(all(
        inspect.fwd_target(x) is None
            for x in self.everything - set([self.fwd])
      ))

  def testIsaChoice(self):
    self.assertIsaChoice(self.choice)
    map(self.assertIsNotAChoice, self.everything - set([self.choice]))

  def testIsaFunc(self):
    funcs = [self.func, self.py_generator]
    map(self.assertIsaFunc, funcs)
    map(self.assertIsNotAFunc, self.everything - set(funcs))

  def testIsaCtorOrData(self):
    ctors = [
        self.int
      , self.char
      , self.string
      , self.empty_string
      , self.float
      , self.just_nil
      , self.io
      , self.true
      , self.false
      , self.tuple
      , self.list
      , self.empty_list
      ]
    map(self.assertIsaCtor, ctors)
    map(self.assertIsNotACtor, self.everything - set(ctors))

    data = ctors + [self.unboxed_int, self.unboxed_char, self.unboxed_float]
    map(self.assertIsData, data)
    map(self.assertIsNotData, self.everything - set(data))

  def testGetChoiceID(self):
    self.assertEqual(inspect.get_choice_id(self.var), self.vid)
    self.assertEqual(inspect.get_choice_id(self.choice), self.cid)
    self.assertTrue(all(
        inspect.get_choice_id(x) is None
            for x in self.everything - set([self.var, self.choice])
      ))

  def testGetVariableID(self):
    self.assertEqual(inspect.get_freevar_id(self.var), self.vid)
    self.assertTrue(all(
        inspect.get_freevar_id(x) is None
            for x in self.everything - set([self.var])
      ))

  def testGetSetID(self):
    self.assertEqual(inspect.get_set_id(self.setgrd), self.sid)
    self.assertTrue(all(
        inspect.get_set_id(x) is None
            for x in self.everything - set([self.setgrd])
      ))

