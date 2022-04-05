import cytest # from ./lib; must be first
from curry.expressions import free, unboxed
from curry import inspect
from curry.interpreter import Interpreter
import curry
import cytest.expression_library

def MAP(*args):
  list(map(*args))

class TestInspect(cytest.expression_library.ExpressionLibTestCase):
  def testIsaTypeError(self):
    self.assertIsa(curry.raw_expr(1), curry.symbol('Prelude.Int'))
    self.assertRaisesRegex(
        TypeError
      , 'arg 2 must be an instance or sequence of curry.objects.CurryNodeInfo objects.'
      , lambda: inspect.isa(curry.raw_expr(1), self.not_a_node)
      )

  def testIsaCurryExpr(self):
    MAP(self.assertIsaCurryExpr, self.everything - set([self.not_a_node]))

  def testIsaPrimitive(self):
    boxed_primitives = [self.int, self.char, self.float]
    unboxed_primitives = [self.unboxed_int, self.unboxed_char, self.unboxed_float]
    primitives = boxed_primitives + unboxed_primitives
    MAP(self.assertIsaPrimitive, primitives)
    MAP(self.assertIsaBoxedPrimitive, boxed_primitives)
    MAP(self.assertIsaUnboxedPrimitive, unboxed_primitives)
    MAP(self.assertIsNotAPrimitive, self.everything - set(primitives))
    MAP(self.assertIsNotABoxedPrimitive, self.everything - set(boxed_primitives))
    MAP(self.assertIsNotAUnboxedPrimitive, self.everything - set(unboxed_primitives))

    # Tests for is_boxed
    not_boxed = unboxed_primitives + [self.not_a_node]
    MAP(self.assertIsBoxed, self.everything - set(not_boxed))
    MAP(self.assertIsNotBoxed, not_boxed)

  def testIsaInt(self):
    MAP(self.assertIsaInt, [self.int, self.unboxed_int])
    self.assertIsaBoxedInt(self.int)
    self.assertIsaUnboxedInt(self.unboxed_int)
    MAP(self.assertIsNotAInt, self.everything - set([self.int, self.unboxed_int]))
    MAP(self.assertIsNotABoxedInt, self.everything - set([self.int]))
    MAP(self.assertIsNotAUnboxedInt, self.everything - set([self.unboxed_int]))

  def testIsaChar(self):
    MAP(self.assertIsaChar, [self.char, self.unboxed_char])
    self.assertIsaBoxedChar(self.char)
    self.assertIsaUnboxedChar(self.unboxed_char)
    MAP(self.assertIsNotAChar, self.everything - set([self.char, self.unboxed_char]))
    MAP(self.assertIsNotABoxedChar, self.everything - set([self.char]))
    MAP(self.assertIsNotAUnboxedChar, self.everything - set([self.unboxed_char]))

  def testIsaFloat(self):
    MAP(self.assertIsaFloat, [self.float, self.unboxed_float])
    self.assertIsaBoxedFloat(self.float)
    self.assertIsaUnboxedFloat(self.unboxed_float)
    MAP(self.assertIsNotAFloat, self.everything - set([self.float, self.unboxed_float]))
    MAP(self.assertIsNotABoxedFloat, self.everything - set([self.float]))
    MAP(self.assertIsNotAUnboxedFloat, self.everything - set([self.unboxed_float]))

  def testIsaIO(self):
    self.assertIsaIO(self.io)
    MAP(self.assertIsNotAIO, self.everything - set([self.io]))

  def testIsaBool(self):
    self.assertIsaTrue(self.true)
    self.assertIsaFalse(self.false)
    MAP(self.assertIsaBool, [self.true, self.false])
    MAP(self.assertIsNotATrue, self.everything - set([self.true]))
    MAP(self.assertIsNotAFalse, self.everything - set([self.false]))
    MAP(self.assertIsNotABool, self.everything - set([self.true, self.false]))

  def testIsaList(self):
    nonempty_lists = [self.list, self.string]
    empty_lists = [self.empty_list, self.empty_string]
    lists = nonempty_lists + empty_lists
    MAP(self.assertIsaCons, nonempty_lists)
    MAP(self.assertIsaNil, empty_lists)
    MAP(self.assertIsaList, lists)
    MAP(self.assertIsNotACons, self.everything - set(nonempty_lists))
    MAP(self.assertIsNotANil, self.everything - set(empty_lists))
    MAP(self.assertIsNotAList, self.everything - set(lists))

  def testIsaTuple(self):
    self.assertIsaTuple(self.tuple)
    MAP(self.assertIsNotATuple, self.everything - set([self.tuple]))

    for good in ['()', '(,)', '(,,)', '(,,,,,,,,)']:
      self.assertTrue(inspect.isa_tuple_name(good))
    for bad in ['', '(', '(,', ',,,,,,,,)', ',', ',,,', ')']:
      self.assertFalse(inspect.isa_tuple_name(bad))

  def testIsaSetGuard(self):
    self.assertIsaSetGuard(self.setgrd)
    MAP(self.assertIsNotASetGuard, self.everything - set([self.setgrd]))

  def testIsaFailure(self):
    self.assertIsaFailure(self.failure)
    MAP(self.assertIsNotAFailure, self.everything - set([self.failure]))

  def testIsaConstraint(self):
    constraints = [self.nonstrict_constraint, self.strict_constraint, self.value_binding]
    MAP(self.assertIsaConstraint, constraints)
    MAP(self.assertIsNotAConstraint, self.everything - set(constraints))

  def testIsaVariable(self):
    self.assertIsaFreevar(self.free)
    MAP(self.assertIsNotAFreevar, self.everything - set([self.free]))

  def testIsaFwd(self):
    self.assertIsaFwd(self.fwd)
    MAP(self.assertIsNotAFwd, self.everything - set([self.fwd]))

    # Tests for fwd_target.
    self.assertEqual(inspect.fwd_target(self.fwd), self.true)
    self.assertTrue(all(
        inspect.fwd_target(x) is None
            for x in self.everything - set([self.fwd])
      ))

  def testIsaChoice(self):
    self.assertIsaChoice(self.choice)
    MAP(self.assertIsNotAChoice, self.everything - set([self.choice]))

  def testIsaFunc(self):
    funcs = [self.func, self.py_generator]
    MAP(self.assertIsaFunc, funcs)
    MAP(self.assertIsNotAFunc, self.everything - set(funcs))

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
    MAP(self.assertIsaCtor, ctors)
    MAP(self.assertIsNotACtor, self.everything - set(ctors))

    data = ctors + [self.unboxed_int, self.unboxed_char, self.unboxed_float]
    MAP(self.assertIsData, data)
    MAP(self.assertIsNotData, self.everything - set(data))

  def testGetChoiceID(self):
    self.assertEqual(inspect.get_choice_id(self.free), self.vid)
    self.assertEqual(inspect.get_choice_id(self.choice), self.cid)
    self.assertTrue(all(
        inspect.get_choice_id(x) is None
            for x in self.everything - set([self.free, self.choice])
      ))

  def testGetVariableID(self):
    self.assertEqual(inspect.get_freevar_id(self.free), self.vid)
    self.assertTrue(all(
        inspect.get_freevar_id(x) is None
            for x in self.everything - set([self.free])
      ))

  def testGetSetID(self):
    self.assertEqual(inspect.get_set_id(self.setgrd), self.sid)
    self.assertTrue(all(
        inspect.get_set_id(x) is None
            for x in self.everything - set([self.setgrd])
      ))

  def testSymbolsAndTypes(self):
    curry.path.insert(0, 'data/curry')
    Peano = curry.import_('Peano')
    Nat = curry.type('Peano.Nat')

    # inspect.types
    self.assertEqual(inspect.types(Peano), {'Nat': Nat})
    self.assertEqual(inspect.gettype(Peano, 'Nat'), Nat)
    self.assertRaises(curry.TypeLookupError, lambda: inspect.gettype(Peano, 'Foo'))
    self.assertRaises(curry.TypeLookupError, lambda: inspect.gettype(Peano, 'add'))
    self.assertRaises(curry.TypeLookupError, lambda: inspect.gettype(Peano, 'O'))

    # inspect.gettype
    Control = curry.import_('Control')
    SetFunctions = curry.import_('Control.SetFunctions')
    self.assertEqual(
        inspect.gettype(Control, 'SetFunctions.Values')
      , curry.type('Control.SetFunctions.Values')
      )
    self.assertEqual(inspect.gettype(Peano, 'Nat'), Nat)

    # inspect.symbols
    public_symbols = {'O': Peano.O, 'S': Peano.S, 'add': Peano.add, 'main': Peano.main}
    self.assertEqual(inspect.symbols(Peano), public_symbols)
    self.assertEqual(inspect.getsymbol(Peano, 'S'), Peano.S)
    self.assertRaises(curry.SymbolLookupError, lambda: inspect.getsymbol(Peano, 'Foo'))
    self.assertRaises(curry.SymbolLookupError, lambda: inspect.getsymbol(Peano, 'Nat'))

    # There are additional symbols for Prelude.Data.
    all_symbols = inspect.symbols(Peano, private=True)
    self.assertTrue(len(all_symbols) > len(public_symbols))

    # inspect.getsymbol
    Data = curry.import_('Data')
    curry.import_('Data.List')
    nub = inspect.getsymbol(Data, 'List.nub')
    self.assertEqual(nub.fullname, 'Data.List.nub')
