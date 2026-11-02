'''Known dictionaries and literal dispatch, through every execution route.'''
import cytest
from curry import icurry
from curry.icurry import types
from unit_optimize import ModuleTestCase, function, ifcalls
from curry.icurry.analysis.literals import literal_switches
import curry, importlib.util, itertools, unittest


SOURCE = '''
undefined :: a
undefined = error "forced"
less :: Int -> Int -> Bool
less x y = x < y
charCompare :: Char -> Char -> Ordering
charCompare x y = compare x y
floatMin :: Float -> Float -> Float
floatMin x y = min x y
poly :: Ord a => a -> a -> Bool
poly x y = x < y
intCase :: Int -> Int
intCase x = case x of 0 -> 10; 1 -> 11; _ -> 12
intAlias :: Int -> Int
intAlias x = intCase (x + 0)
intMissing :: Int -> Int
intMissing x = case x of 0 -> 10; 1 -> 11
charCase :: Char -> Int
charCase x = case x of 'a' -> 10; 'z' -> 11; _ -> 12
charMissing :: Char -> Int
charMissing x = case x of 'a' -> 10; 'z' -> 11
hugeCase :: Int -> Int
hugeCase x = case x of 18446744073709551616 -> 10; 0 -> 11; _ -> 12
intRigid = intCase x where x free
intLocal = let x = (0 ? 1) :: Int in (intCase x, x)
floatGreater :: Float -> Float -> Bool
floatGreater x y = x > y
floatCompare :: Float -> Float -> Ordering
floatCompare x y = compare x y
shared = (0 ? 1) < (1 :: Int)
diagonal = let x = (0 ? 1) :: Int in (x < 1, x)
lazyAnd = False && undefined
data Probe = Probe
instance Eq Probe where
  _ == _ = undefined
instance Ord Probe where
  _ <= _ = False
instance Show Probe where
  showsPrec _ _ s = 'x' : s
lazyLess = (undefined :: Probe) < undefined
lazyGreater = (undefined :: Probe) > undefined
lazyGE = (undefined :: Probe) >= undefined
lazyMin = show (min undefined Probe)
lazyMax = show (max undefined Probe)
lazyShow = show (undefined :: Probe)
'''


class TestPerfcomp(ModuleTestCase):
  def test_deep_fallback(self):
    zero = types.ILit(types.IInt(0))
    result = types.ICCall('Prelude.[]', [])
    for _ in range(2000):
      result = types.ICCall('Prelude.:', [zero, result])
    helper = function('case_COMPLEXCASE0', 2, [(1, [0]), (2, [1])],
        types.ICaseCons(2, [
          types.IConsBranch('Prelude.True', 0, types.IBlock([], [], types.IReturn(zero))),
          types.IConsBranch('Prelude.False', 0, types.IBlock([], [], types.IReturn(result)))]))
    helper.vis = types.PRIVATE
    caller = function('main', 1, [(1, [0])], types.IReturn(types.IFCall(
        helper.fullname, [types.IVar(1), types.IFCall('Prelude.eqInt', [types.IVar(1), zero])])))
    module = types.IModule('M', [], [], [caller, helper])
    literal_switches(caller, {'M': module}, module)
    self.assertIsInstance(caller.body.block.stmt, types.ICaseLit)

  def test_compiled_structure(self):
    name = self.write('PerfcompShape', SOURCE)
    module = self.icurry_of(name, inline=True)
    self.assertIn('Prelude.ltEqInt', ifcalls(module.functions['less']))
    self.assertIn('Prelude.eqInt', ifcalls(module.functions['less']))
    for method in ('less', 'charCompare', 'floatMin'):
      self.assertFalse(any('._def#' in call for call in ifcalls(module.functions[method])))
    specialized = [f for f in module.functions.values() if f.name.startswith('_dictspec')]
    self.assertTrue(specialized)
    self.assertTrue(any('Prelude.ltEqChar' in ifcalls(f) for f in specialized))
    self.assertFalse(any('._def#' in call for f in specialized for call in ifcalls(f)))
    self.assertIn('Prelude.<._#lambda', ifcalls(module.functions['poly']))
    self.assertIn('Prelude.apply', ifcalls(module.functions['poly']))
    switch = module.functions['intCase'].body.block.stmt
    self.assertIsInstance(switch, types.ICaseLit)
    self.assertTrue(switch.rigid)
    self.assertEqual([b.lit.value for b in switch.branches if b.lit is not None], [0, 1])
    self.assertIn('Prelude.eqInt', ifcalls(module.functions['intCase']))
    self.assertEqual(switch.rigid, 2)
    fallback = switch.branches[-1].block.stmt.expr
    self.assertIn('._litfallback', fallback.symbolname)
    alias_call = module.functions['intAlias'].body.block.stmt.expr
    alias_switch = module.functions[alias_call.symbolname.rsplit('.', 1)[1]].body.block.stmt
    self.assertIsInstance(alias_switch, types.ICaseLit)
    self.assertEqual([b.lit.value for b in alias_switch.branches if b.lit is not None], [0, 1])
    # The optimized form survives the image's summary codec as well.
    self.assertEqual(icurry.json.loads(icurry.json.dumps(switch)), switch)

  @cytest.hardreset
  def test_values_all_routes(self):
    modes = [dict(interpret='off', jit='off'), dict(interpret='all', jit='off'),
             dict(interpret='all', jit='off', checker=True)]
    if importlib.util.find_spec('llvmlite') is not None:
      modes.append(dict(interpret='all', jit='eager', jit_backend='llvm'))
    for flags in modes:
      with self.subTest(flags=flags):
        self.reload(**flags)
        module = self.import_(self.write('PerfcompValues', SOURCE))
        for name, inputs in [('intCase', [0, 1, 2, -1, 2**80]),
                             ('charCase', ['a', 'z', 'b', '\U0001f600'])]:
          self.assertEqual([curry.eval(getattr(module, name)(curry.Char(x) if isinstance(x, str) else x)).one() for x in inputs],
                           [10, 11] + [12] * (len(inputs) - 2))
        for name, inputs in [('intMissing', [0, 1, 2, 2**80]),
                             ('charMissing', ['a', 'z', 'b'])]:
          self.assertEqual([list(curry.eval(getattr(module, name)(curry.Char(x) if isinstance(x, str) else x))) for x in inputs],
                           [[10], [11]] + [[]] * (len(inputs) - 2))
        self.assertEqual([curry.eval(module.hugeCase(x)).one()
                          for x in [2**64, 0, 1, 2**80]], [10, 11, 12, 12])
        with self.assertRaises(curry.SuspensionError):
          list(curry.eval(module.intRigid))
        self.assertTrue(curry.eval(module.floatGreater(float('nan'), 0.0)).one())
        self.assertEqual(curry.eval(module.floatCompare(float('nan'), 0.0)).one().symbol.name, 'GT')
        self.assertEqual(curry.eval(module.charCompare(curry.Char('z'), curry.Char('a'))).one().symbol.name, 'GT')
        self.assertEqual(curry.eval(module.floatMin(2.5, 1.5)).one(), 1.5)
        self.assertEqual(list(curry.eval(module.shared)), [True, False])
        self.assertEqual(list(curry.eval(module.diagonal)), [(True, 0), (False, 1)])
        self.assertEqual(list(curry.eval(module.intLocal)), [(10, 0), (11, 1)])
        for goal, expected in [('lazyAnd', False), ('lazyLess', False),
                               ('lazyGreater', True), ('lazyGE', False),
                               ('lazyMin', 'x'), ('lazyMax', 'x'), ('lazyShow', 'x')]:
          self.assertEqual(curry.eval(getattr(module, goal)).one(), expected)

  @cytest.hardreset
  def test_original_graph_fallback(self):
    source = SOURCE + """
choiceCase = let x = (0 ? (1 ? 2)) :: Int in (intCase x, x)
freeCase = let x free in (intCase x, x)
constrainedFree = x =:= (0 ? (1 ? (2 :: Int))) &> (intCase x, x) where x free
charChoice = charCase ('a' ? ('z' ? 'b'))
positive :: Int
positive = 1 ? (2 * positive) ? (2 * positive + 1)
fraction :: Float -> Int -> Float
fraction m i = if i == 0 then 0
               else fraction (m / 10) (i `div` 10) + m * fromInt (i `mod` 10)
positiveFloat = fromInt positive + fraction 0.1 positive
floatGraph = positiveFloat ? 0 ? (0 - positiveFloat)
freeGraph = x =:= floatGraph &> x where x free
"""
    modes = [dict(interpret='off', jit='off'), dict(interpret='all', jit='off')]
    if importlib.util.find_spec('llvmlite') is not None:
      modes.append(dict(interpret='all', jit='eager', jit_backend='llvm'))
    for flags in modes:
      self.reload(**flags)
      modules = []
      for enabled in (False, True):
        name = self.write('GraphEnabled' if enabled else 'GraphDisabled', source)
        module = self.load_icurry(name)
        if not enabled:
          module.update_metadata({'cxx.opt.literal_switches': True})
        modules.append(cytest.raw.import_(module, currypath=self.currypath))
      for goal in ('choiceCase', 'charChoice', 'constrainedFree', 'freeCase'):
        results = []
        for module in modules:
          try:
            results.append(list(curry.eval(getattr(module, goal))))
          except curry.SuspensionError:
            results.append('suspended')
        self.assertEqual(results[0], results[1], (flags, goal))
      for goal in ('floatGraph', 'freeGraph'):
        results = [list(itertools.islice(curry.eval(getattr(module, goal)), 8))
                   for module in modules]
        self.assertEqual(results[0], results[1], (flags, goal))
      # The deterministic route retains an unboxed switch beside the probe.
      if flags['interpret'] == 'off':
        from unit_cxx_emit import generated_text
        text = generated_text(modules[1])
        self.assertIn('false, true)', text)
        self.assertIn('switch(NodeU{', text)

  def test_all_primitive_instances(self):
    for typename in ('Int', 'Char', 'Float'):
      for method in ('<', '>', '>=', '/=', 'compare', 'min', 'max'):
        name = self.write('PerfcompMethod', '''
          method :: %s -> %s -> %s
          method x y = %s
          ''' % (typename, typename,
                 'Ordering' if method == 'compare' else typename if method in ('min', 'max') else 'Bool',
                 '%s x y' % method if method.isalpha() else 'x %s y' % method))
        module = self.icurry_of(name, inline=True)
        self.assertNotIn('Prelude._def#%s#Prelude.Ord' % method,
                         ifcalls(module.functions['method']))
        self.assertNotIn('Prelude._def#/=#Prelude.Eq', ifcalls(module.functions['method']))
      name = self.write('PerfcompShow', 'method :: %s -> String\nmethod x = show x\n' % typename)
      module = self.icurry_of(name, inline=True)
      self.assertNotIn('Prelude._def#show#Prelude.Show', ifcalls(module.functions['method']))


if __name__ == '__main__':
  unittest.main()
