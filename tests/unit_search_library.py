'''The typed search facade and Sprite's documented weak capsule semantics.'''
import cytest # from ./lib; must be first
import collections, curry, hashlib, json, pathlib, unittest, zlib
from curry import config, icurry


class TestSearchLibrary(cytest.TestCase):
  def setUp(self):
    super().setUp()
    self.sf = curry.import_('Control.Search.SetFunctions')
    self.native = curry.import_('Control.SetFunctions')
    self.unsafe = curry.import_('Control.Search.Unsafe')
    self.io = curry.import_('Control.Search.AllValues')
    self.P = curry.import_('Prelude')

  def goal(self, text, name='goal'):
    module = curry.compile('''
import Control.Search.SetFunctions
import qualified Control.SetFunctions as Native
import qualified Control.Search.Unsafe as U
import qualified Control.Search.AllValues as A
''' + text)
    return list(curry.eval(module[name]))

  def test_pinned_products(self):
    root = pathlib.Path(__file__).resolve().parents[1] / 'curry/lib/Control/Search'
    hashes = {
        'SetFunctions': 'af4ef5477442efe5a5dad820a8e6b1446fff36db56bf8d332110e92e7251af33',
        'Unsafe': 'abefc2ffa46b599e73ed812c9491856d9a2f5a5085b6869832cda4512f75256b',
        'AllValues': '7e8843179c950b6a793c5d33d26cc8513bf60fd5b3313b162ca0efe201989512',
      }
    for name, digest in hashes.items():
      with self.subTest(module=name):
        self.assertEqual(hashlib.sha256((root / (name + '.curry')).read_bytes()).hexdigest(), digest)
        text = icurry.readcurry.load(str(root / (name + '.icy')))
        data = icurry.json.loads(zlib.decompress((root / (name + '.json.z')).read_bytes()))
        self.assertEqual(text, data)
        self.assertEqual(text.fullname, 'Control.Search.' + name)
        installed = pathlib.Path(config.system_curry_path()) / 'Control/Search/.curry'
        product = installed / config.intermediate_subdir() / (name + '.so')
        self.assertTrue(product.is_file(), name)

  def test_canonical_values_and_types(self):
    values = curry.term(self.sf.set0(3))
    self.assertEqual(curry.typeof(values, defaulted=True), 'Values Int')
    self.assertEqual(list(curry.eval(self.sf.sortValues(values))), [[3]])
    self.assertEqual(list(curry.eval(self.native.sortValues(values))), [[3]])
    self.assertEqual(list(curry.eval(self.sf.sortValues(
                                   curry.term(self.native.set0(4))))), [[4]])
    with self.assertRaises(curry.CurryTypeError):
      curry.term(self.sf.sortValues(True))

  def test_typed_operation_surface(self):
    values = curry.term(self.sf.set0(7))
    for name in ('isEmpty', 'notEmpty', 'choose', 'chooseValue', 'select',
                 'selectValue', 'minValue', 'maxValue', 'sortValues',
                 'values2list', 'getSome', 'getSomeValue', 'printValues'):
      with self.subTest(name=name):
        expression = curry.term(self.sf[name](values))
        self.assertTrue(curry.typeof(expression))
        if name != 'printValues':
          self.assertEqual(len(list(curry.eval(expression))), 1)
    for name in ('allValues', 'allValuesDFS', 'oneValue', 'oneValueDFS',
                 'someValue', 'isFail'):
      with self.subTest(name=name):
        expression = curry.term(self.unsafe[name](7))
        self.assertTrue(curry.typeof(expression))
        self.assertEqual(len(list(curry.eval(expression))), 1)
    for name in ('getAllValues', 'getAllValuesDFS', 'getOneValue', 'getOneValueDFS'):
      with self.subTest(name=name):
        expression = curry.term(self.io[name](7))
        self.assertTrue(str(curry.typeof(expression, defaulted=True)).startswith('IO '))
        self.assertEqual(len(list(curry.eval(expression))), 1)

  def test_print_values(self):
    proc = cytest.run_in_subprocess("""
import curry
sf = curry.import_('Control.Search.SetFunctions')
assert list(curry.eval(sf.printValues(sf.set0(7)))) == [()]
""", timeout=60, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, '7\n')

  def test_observers(self):
    self.assertEqual(self.goal('''
goal :: (Bool, Bool, Bool, Int, Int, Int, Int, Int, [Int], [Int])
goal = let vs = set0 (3 ? 1 ? 3) in
  (isEmpty vs, notEmpty vs, valueOf 3 vs, foldValues (+) 0 vs,
   minValue vs, maxValue vs, minValueBy compare vs, maxValueBy compare vs,
   sortValues (filterValues (>1) (mapValues (+1) vs)), sortValuesBy (>=) vs)
'''), [(False, True, True, 7, 1, 3, 1, 3, [2,4,4], [3,3,1])])

  def test_selection(self):
    self.assertEqual(self.goal('''
goal :: [(Int, [Int])]
goal = sortValues (set1 (\\vs -> let (x,rest) = choose vs
                              in (x, sortValues rest)) (set0 (1 ? 2 ? 2)))
'''), [[(1,[2,2]), (2,[1,2]), (2,[1,2])]])
    self.assertEqual(self.goal('goal = selectValue (set0 (7 :: Int))'), [7])
    self.assertEqual(self.goal('goal = chooseValue (set0 (7 :: Int))'), [7])
    self.assertEqual(self.goal('goal = isEmpty (set0 (failed :: Int))'), [True])

  def test_advisory_strategies_and_arities(self):
    for strategy in ('dfsStrategy', 'bfsStrategy', 'idsStrategy',
                     'idsStrategyWith 1 (+1)', 'diagStrategy', 'failed'):
      with self.subTest(strategy=strategy):
        self.assertEqual(self.goal('goal = sortValues (set0With (%s) '
                                   '(1 ? 2 ? 2 :: Int))' % strategy), [[1,2,2]])
    for n in range(1, 8):
      args = ['x%d' % i for i in range(n)]
      function = '(\\%s -> (%s) ? 99)' % (' '.join(args), ' + '.join(args))
      for suffix in ('', 'With bfsStrategy'):
        with self.subTest(arity=n, suffix=suffix):
          self.assertEqual(self.goal('goal :: [Int]\ngoal = sortValues '
              '(set%d%s %s %s)' % (n, suffix, function,
                                    ' '.join(str(i+1) for i in range(n)))),
                           [[n*(n+1)//2, 99]])

  def test_weak_encapsulation(self):
    # PAKCS 3.10.0: this captured-choice goal gives "[1,2]" once.
    # Sprite's D28 rule gives singleton sets, one per outside choice.
    for call in ('set0', 'set0With bfsStrategy'):
      self.assertEqual(sorted(self.goal('goal :: [Int]\ngoal = let x = 1 ? 2 '
          'in sortValues (%s x)' % call)), [[1], [2]])
    # PAKCS 3.10.0 suspends on the free argument; Sprite narrows outside.
    self.assertEqual(sorted(self.goal('''
f True = 1 :: Int
f False = 2
goal = sortValues (set1 f x) where x free
''')), [[1], [2]])

  def test_unsafe_free_variable(self):
    # PAKCS 3.10.0: "*** Evaluation suspended!" for this goal.
    # Sprite leaves the variable free instead of enumerating Bool inside.
    module = curry.compile("""
import Control.Search.Unsafe
freeValue :: [Bool]
freeValue = allValues x where x free
""")
    self.assertEqual([curry.show(v) for v in curry.eval(module.freeValue)],
                     ['[_a]'])

  def test_function_choice_stays_outside(self):
    # Corpus basic03: PAKCS groups [G_T,H_T] and [G_F,H_F]; Sprite keeps
    # the choice of the function argument outside, giving four singletons.
    for operation in ('set1', 'Native.set1'):
      with self.subTest(operation=operation):
        self.assertEqual(sorted(self.goal("""
f :: Int -> Int
f = (+1) ? (*2)
goal :: [Int]
goal = sortValues (%s f 3)
""" % operation)), [[4], [6]])

  def test_free_narrowing_stays_outside(self):
    # PAKCS 3.10.0: "*** Evaluation suspended!" for this expression.
    # Sprite narrows the outside Bool, producing one singleton per binding.
    self.assertEqual(sorted(self.goal("""
goal :: [Bool]
goal = U.allValues (not x) where x free
""")), [[False], [True]])

  def test_wrapper_boundaries(self):
    for name in ('allValues', 'allValuesDFS'):
      with self.subTest(name=name):
        self.assertEqual(sorted(self.goal('goal :: [Int]\ngoal = '
            'let x = 1 ? 2 in U.%s x' % name)), [[1], [2]])
    for name in ('oneValue', 'oneValueDFS'):
      with self.subTest(name=name):
        values = self.goal('goal :: Maybe Int\ngoal = '
                           'let x = 1 ? 2 in U.%s x' % name)
        self.assertEqual(sorted(str(v) for v in values), ['Just 1', 'Just 2'])
    self.assertEqual(self.goal('goal :: IO [Int]\ngoal = '
                              'let x = 7 in A.getAllValues x'), [[7]])
    self.assertEqual(self.goal('goal :: IO (Maybe Int)\ngoal = '
                              'let x = 7 in A.getOneValue x'), [self.P.Just(7)])

  def test_io_selections(self):
    self.assertEqual(self.goal('''
goal :: IO (Maybe Int, Maybe Int, Maybe (Int,[Int]))
goal = do
  empty <- getSomeValue (set0 failed)
  one <- getSomeValue (set0 7)
  rest <- getSome (set0 7)
  return (empty, one, fmap (\\(x,vs) -> (x,sortValues vs)) rest)
'''), [(self.P.Nothing, self.P.Just(7), self.P.Just((7, [])))])
    self.assertEqual(self.goal('''
goal :: IO Bool
goal = do
  x <- getSome (set0 (failed :: Int))
  return (case x of Nothing -> True; Just _ -> False)
'''), [True])

  def test_unsafe_and_io_wrappers(self):
    self.assertEqual(self.goal('''
goal :: ([Int], [Int], Maybe Int, Maybe Int, Int, Bool, Bool)
goal = (U.allValues (7 ? 7), U.allValuesDFS 8, U.oneValue 9,
        U.oneValueDFS failed, U.someValue 10, U.isFail failed, U.isFail 1)
'''), [([7,7], [8], self.P.Just(9), self.P.Nothing, 10, True, False)])
    self.assertEqual(self.goal('''
goal :: IO ([Int], [Int], Maybe Int, Maybe Int, [Int])
goal = do
  a <- A.getAllValues (7 ? 7)
  b <- A.getAllValuesDFS 8
  c <- A.getOneValue 9
  d <- A.getOneValueDFS failed
  e <- A.getAllFailures (1 ? 2) (\\x -> x =:= 1)
  return (a,b,c,d,e)
'''), [([7,7], [8], self.P.Just(9), self.P.Nothing, [2])])

  def test_rewriting_not_implemented_at_call(self):
    for name in ('rewriteAll', 'rewriteSome'):
      symbol = self.unsafe[name]
      expression = curry.term(symbol(1))
      self.assertTrue(str(curry.typeof(expression)))
      with self.assertRaisesRegex(curry.EvaluationError, 'not implemented'):
        list(curry.eval(expression))


class TestNativeCapsuleFinding(cytest.TestCase):
  def setUp(self):
    # Check compilation and process completion outside the expected-failure
    # test body, so a crash or timeout is a real error rather than an xfail.
    code = """
import curry, json
curry.reset(interpret='off')
curry.path.insert(0, 'data/curry/search_setfunctions')
module = curry.import_('NativeFlightCapsule')
print(json.dumps([curry.show(v) for v in curry.eval(module.main)]))
"""
    proc = cytest.run_in_subprocess(code, timeout=60, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    values = json.loads(proc.stdout)
    print('NativeFlightCapsule results:', dict(collections.Counter(values)))
    self.actual = '\n'.join(values)

  @unittest.expectedFailure
  def test_shortest_itinerary(self):
    # Issue #171. PAKCS 3.10.0: [LH469,LH10] once. The native capsules also
    # admit the longer [NWA92,KL1783] and repeat the answers.
    self.assertSameResultMultiset(self.actual, '[LH469,LH10]')


if __name__ == '__main__':
  unittest.main()
