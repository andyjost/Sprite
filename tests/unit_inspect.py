import cytest # from ./lib; must be first
import curry
from curry import inspect
from curry.expressions import (
    unboxed
  , _setgrd, fail, _strictconstr, _nonstrictconstr, _valuebinding, var, fwd
  , choice
  )

class TestInspect(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    prelude = curry.import_('Prelude')
    cls.not_a_node = int
    cls.int = curry.expr(5)
    cls.unboxed_int = 5
    cls.char = curry.expr('a')
    cls.unboxed_char = 'a'
    cls.string = curry.expr('why hello')
    cls.empty_string = curry.expr('')
    cls.float = curry.expr(1.0)
    cls.unboxed_float = 1.0
    cls.just_nil = curry.expr(prelude.Just, [])
    cls.io = curry.expr(prelude.IO, prelude.True)
    cls.true = curry.expr(True)
    cls.false = curry.expr(False)
    cls.tuple = curry.expr((1,2,3))
    cls.list = curry.expr([1,2,3])
    cls.empty_list = curry.expr([])
    cls.py_generator = curry.expr(iter([1,2]))
    cls.failure = curry.expr(fail)
    cls.fwd = curry.expr(fwd(prelude.True))
    cls.vid = 2
    cls.var = curry.expr(var(cls.vid))
    cls.cid = 3
    cls.choice = curry.expr(choice(3, 0, 1))
    cls.nonstrict_constraint = curry.expr(_nonstrictconstr(True, (cls.var, False)))
    cls.sid = 7
    cls.setgrd = curry.expr(_setgrd(cls.sid, True))
    cls.strict_constraint = curry.expr(_strictconstr(True, (var(1), var(2))))
    cls.value_binding = curry.expr(_valuebinding(True, (var(1), unboxed(2))))
    cls.func = curry.expr(prelude.head, getattr(prelude, '[]'))
    cls.everything = set([
        cls.not_a_node
      , cls.int
      , cls.unboxed_int
      , cls.char
      , cls.unboxed_char
      , cls.string
      , cls.empty_string
      , cls.float
      , cls.unboxed_float
      , cls.just_nil
      , cls.io
      , cls.true
      , cls.false
      , cls.tuple
      , cls.list
      , cls.empty_list
      , cls.py_generator
      , cls.failure
      , cls.fwd
      , cls.var
      , cls.choice
      , cls.nonstrict_constraint
      , cls.setgrd
      , cls.strict_constraint
      , cls.value_binding
      , cls.func
      ])

  @classmethod
  def tearDownClass(cls):
    keys = [k for k in  cls.__dict__ if not k.startswith('_')]
    for k in keys:
      delattr(cls, k)

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
    self.assertIsaVariable(self.var)
    map(self.assertIsNotAVariable, self.everything - set([self.var]))

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
    self.assertEqual(inspect.get_variable_id(self.var), self.vid)
    self.assertTrue(all(
        inspect.get_variable_id(x) is None
            for x in self.everything - set([self.var])
      ))

  def testGetSetID(self):
    self.assertEqual(inspect.get_set_id(self.setgrd), self.sid)
    self.assertTrue(all(
        inspect.get_set_id(x) is None
            for x in self.everything - set([self.setgrd])
      ))

