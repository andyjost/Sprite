import cytest # from ./lib; must be first
from curry.expressions import free, unboxed
from curry import backends, icurry, inspect
from curry.common import T_CTOR
from curry.interpreter import Interpreter
import curry, gc, types, unittest
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

  def testTypeCaches(self):
    '''
    is_boxed and isa_unboxed_primitive cache their result per type.  The
    cache must answer as the checks it replaces do, and it must notice a class
    registered with an ABC after the cache saw its instances.
    '''
    node = curry.raw_expr(1)
    for _ in range(2):
      self.assertTrue(inspect.is_boxed(node))
      for value in [1, 1.0, 'a', True, None, b'ab', memoryview(b'ab'), 1j]:
        self.assertFalse(inspect.is_boxed(value))
      for value in [1, 1.0, 'a', True, memoryview(b'a'), iter([])]:
        self.assertTrue(inspect.isa_unboxed_primitive(value))
      for value in [node, None, [], {}, b'ab']:
        self.assertFalse(inspect.isa_unboxed_primitive(value))
    # An object that is not a node answers through its is_boxed attribute.
    self.assertTrue(inspect.is_boxed(types.SimpleNamespace(is_boxed=True)))
    self.assertFalse(inspect.is_boxed(types.SimpleNamespace(is_boxed=False)))
    self.assertFalse(inspect.is_boxed(types.SimpleNamespace()))
    # A class registered after the cache saw it.
    class Boxed(object):
      pass
    class Unboxed(object):
      pass
    self.assertFalse(inspect.is_boxed(Boxed()))
    self.assertIsNone(inspect.tag_of(Unboxed()))
    backends.Node.register(Boxed)
    icurry.IUnboxedLiteral.register(Unboxed)
    self.assertTrue(inspect.is_boxed(Boxed()))
    self.assertTrue(inspect.isa_unboxed_primitive(Unboxed()))
    self.assertEqual(inspect.tag_of(Unboxed()), T_CTOR)

  def testTypeCachesWithSpoofedClass(self):
    '''
    isinstance also consults __class__, which a proxy or a mock may set per
    instance.  The caches key on the type, so for such an object they must
    fall back to the uncached check, whatever the first instance of the type
    answered.
    '''
    node = curry.raw_expr(1)
    def proxy_class():
      class Proxy(object):
        def __init__(self, cls):
          self._cls = cls
        @property
        def __class__(self):
          return self._cls
      return Proxy
    for order in [(type(node), int), (int, type(node))]:
      Proxy = proxy_class()
      objects = [Proxy(cls) for cls in order]
      for _ in range(2):
        for obj in objects:
          self.assertEqual(
              inspect.is_boxed(obj), isinstance(obj, backends.Node), obj._cls
            )
          self.assertEqual(
              inspect.isa_unboxed_primitive(obj)
            , isinstance(obj, icurry.IUnboxedLiteral), obj._cls
            )

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

  @cytest.skipIfInterpreted('the test expects a module loaded from its object')
  def testGetICurry(self):
    '''
    A module loaded from its compiled code carries a bill of materials whose
    functions have no body.  geticurry reads the ICurry of the module from
    its file and finds a function there by name (issue #38).
    '''
    curry.path.insert(0, 'data/curry')
    Peano = curry.import_('Peano')
    bom = getattr(Peano, '.icurry')
    self.assertIsInstance(Peano.add.icurry.body.block, icurry.IExempt)
    imodule = inspect.geticurry(Peano)
    self.assertIsInstance(imodule, icurry.IModule)
    self.assertIsNot(imodule, bom)
    self.assertEqual(imodule.fullname, 'Peano')
    # The file is read once.
    self.assertIs(inspect.geticurry(Peano), imodule)
    add = inspect.geticurry(Peano.add)
    self.assertIs(add, imodule.functions['add'])
    self.assertNotIsInstance(add.body.block, icurry.IExempt)
    self.assertIn('add:', str(add))
    self.assertNotIn('exempt', str(add))
    self.assertIn('exempt', str(Peano.add.icurry))
    # A constructor and a type give their ICurry.
    self.assertIs(inspect.geticurry(Peano.S), Peano.S.icurry)
    Nat = curry.type('Peano.Nat')
    self.assertIs(inspect.geticurry(Nat), Nat.icurry)
    # A module compiled from a string.
    M = curry.compile('f :: Int -> Int\nf x = x + 1')
    f = inspect.geticurry(M.f)
    self.assertIsInstance(f, icurry.IFunction)
    self.assertNotIsInstance(f.body.block, icurry.IExempt)
    self.assertIs(f, inspect.geticurry(M).functions['f'])

  @cytest.skipIfInterpreted(
      'the test expects compiled code; testGetImplInterpreted covers the bytecode'
    )
  def testGetImpl(self):
    '''
    The code of a step function, on the backend of the session (issue #38).
    '''
    curry.path.insert(0, 'data/curry')
    Peano = curry.import_('Peano')
    code = inspect.getimpl(Peano.add)
    self.assertIsInstance(code, str)
    self.assertEqual(code, Peano.add.getimpl())
    prim = curry.symbol('Prelude.prim_showFloatLiteral')
    if curry.flags['backend'] == 'py':
      self.assertRegex(code, r'(^|\n)def \w+\(rts, _0\):')
      self.assertIn('Peano.add', code)
      self.assertIn('prim_showFloatLiteral', inspect.getimpl(prim))
    else:
      lines = code.splitlines()
      self.assertEqual(lines[0], '/****** Peano.add ******/')
      self.assertEqual(
          lines[1]
        , 'tag_type CyF5Peano3add(RuntimeState * rts, Configuration * C)'
        )
      self.assertEqual(lines[-1], '}')
      self.assertIn('rts->hnf(C, &_1, &CyD5Peano3Nat);', code)
      self.assertNotIn('Peano.main', code)
      self.assertRaisesRegex(
          ValueError
        , "no implementation code available for "
          r"'Prelude.prim_showFloatLiteral': it is a built-in of the C\+\+ "
          "runtime"
        , lambda: inspect.getimpl(prim)
        )
    # A constructor has no code.
    self.assertRaisesRegex(
        ValueError, "no implementation code available for 'Peano.O'"
      , lambda: inspect.getimpl(Peano.O)
      )
    self.assertRaisesRegex(
        ValueError, "no implementation code available for 'Peano.O'"
      , Peano.O.getimpl
      )
    self.assertRaises(TypeError, lambda: inspect.getimpl(42))

  @unittest.skipUnless(
      curry.flags['backend'] == 'cxx'
    , 'the ICurry interpreter belongs to the C++ runtime'
    )
  @cytest.hardreset
  def testGetImplInterpreted(self):
    '''
    The bytecode of an interpreted function, with its constants.  The
    inliner is off: main would build the sum in place of the call.
    '''
    gc.collect()
    curry.reload({'backend': 'cxx', 'interpret': 'new', 'inline_budget': 0})
    M = curry.compile(
        'double :: Int -> Int\ndouble x = x + x\nmain :: Int\nmain = double 21'
      , mode='module'
      )
    code = inspect.getimpl(M.double)
    lines = code.splitlines()
    self.assertEqual(lines[0], '/****** %s ******/' % M.double.fullname)
    self.assertRegex(
        lines[1]
      , r'^bytecode: \d+ units, \d+ constants, \d+ registers, \d+ variables, '
        r'stack \d+$'
      )
    self.assertRegex(lines[-1], r'^ *\d+ RET_NODE k0<plusInt> 2$')
    code = inspect.getimpl(M.main)
    self.assertIn("PUSH_CONST k0<('I', 21)>", code)
    self.assertIn('RET_NODE k1<double> 1', code)
    self.assertEqual(code, M.main.getimpl())
