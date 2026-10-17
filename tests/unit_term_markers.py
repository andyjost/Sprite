'''The text and marker routes, before the Results and solve lane.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect
import os

FLOW_PATH = os.path.join(os.path.dirname(__file__), 'data', 'curry', 'flows')

class TestTermMarkers(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)
    self.P = curry.import_('Prelude')

  def values(self, goal):
    return list(curry.eval(goal, converter='topython'))

  def test_parse_annotations_and_composition(self):
    R = curry.import_('Rule')
    for imports in ([R], ['Rule']):
      g = curry.parse('rule "a" ins :: String where ins free', imports=imports)
      self.assertEqual(curry.typeof(g), '[Char]')
      self.assertEqual(list(g.free_vars), ['ins'])
      self.assertIsInstance(g.free_vars['ins'], curry.Var)
      self.assertEqual(self.values(self.P.length(g)), [4, 4])
    self.assertEqual(self.values(curry.parse('1 + 2 :: Float')), [3.0])
    self.assertEqual(self.values(curry.parse('(read "5") :: Int')), [5])
    with self.assertRaises(curry.CompileError):
      curry.parse('not b where b free :: Bool')

  def test_parse_free_clause_and_order(self):
    g = curry.parse('(y =:= 2, x =:= 1) where x, y free')
    self.assertEqual(list(g.free_vars), ['y', 'x'])
    self.assertEqual(list(self.P.id(g).free_vars), ['y', 'x'])
    self.assertEqual(self.values(g), [(True, True)])
    local = curry.parse('not b where b free -- local')
    self.assertEqual(local.free_vars, {})
    self.assertEqual(self.values(local), [True, False])

  def test_parse_defaults_at_evaluation(self):
    g = curry.parse('1 + 2')
    self.assertEqual(curry.typeof(g), 'Num a => a')
    self.assertEqual(self.values(g), [3])
    g = curry.parse('read "5"')
    self.assertEqual(curry.typeof(g), 'Read a => a')
    with self.assertRaises(curry.DefaultingError) as caught:
      curry.eval(g)
    self.assertIn('cannot handle the overloaded goal read "5"', str(caught.exception))
    self.assertIn('Cannot handle arbitrary overloaded top-level expressions', str(caught.exception))

  def test_parse_error_positions(self):
    for text, position in [('1 + )', (1, 5)), ('1 +\n )', (2, 2))]:
      with self.assertRaises(curry.CompileError) as caught:
        curry.parse(text)
      error = caught.exception
      self.assertEqual((error.line, error.column), position)
      self.assertTrue(error.report)
      self.assertNotIn('compiled_expression', str(error))
      self.assertNotIn('.curry', str(error))

  def test_bare_string_and_string_term(self):
    with self.assertRaises(curry.ConversionError) as caught:
      curry.eval('1 + 2')
    self.assertIn('parse', str(caught.exception))
    self.assertIn('term', str(caught.exception))
    self.assertEqual(self.values(curry.term('1 + 2')), ['1 + 2'])

  def test_variable_type_prevents_second_type(self):
    x = curry.free('x')
    self.P.chr(x)
    self.assertEqual(curry.typeof(x), 'Int')
    with self.assertRaises(curry.CurryTypeError):
      self.P['not'](x)
    x = curry.free('x', type='Int')
    with self.assertRaises(curry.CurryTypeError):
      self.P['not'](x)

  def test_variable_numeric_type_after_defaulting(self):
    x = curry.free('x')
    self.P['+'](x, 1)
    self.assertEqual(curry.typeof(x), 'Int')
    with self.assertRaises(curry.CurryTypeError):
      self.P['not'](x)

  def test_variable_partial_type(self):
    x = curry.free('xs')
    self.P.length(x)
    self.assertEqual(curry.typeof(x), 'Data a => [a]')
    self.P['++'](x, [True])
    self.assertEqual(curry.typeof(x), '[Bool]')
    with self.assertRaises(curry.CurryTypeError):
      self.P['++'](x, [1])

  def test_variable_identity_across_goals_and_old_builder(self):
    x = curry.free('x')
    for n in (1, 2):
      goal = (self.P['=:='](x, n), x, x)
      self.assertEqual(self.values(goal), [(True, n, n)])
    node = curry.expr((x, x))
    left, right = (inspect.fwd_chain_target(arg) for arg in node.successors)
    self.assertEqual(left.id(), right.id())
    self.assertEqual(str(curry.raw_expr(x)), '_a')

  def test_names_and_duplicates(self):
    x, y = curry.free('x'), curry.free('y')
    a, b = curry.free(), curry.free()
    self.assertEqual(str(curry.term((b, a, y, b, x))), '(_a,_b,y,_a,x)')
    self.assertNotEqual(self.P.id(x), self.P.id(y))
    self.assertEqual(self.P.id(x), self.P.id(x))
    self.assertEqual(hash(self.P.id(x)), hash(self.P.id(x)))
    self.assertEqual(list(curry.term((y, x, y)).free_vars), ['y', 'x'])
    with self.assertRaises(curry.CurryTypeError):
      self.P['=:='](x, curry.free('x'))
    with self.assertRaises(curry.CurryTypeError):
      curry.eval((x, curry.free('x')))

  def test_anonymous_occurrences(self):
    a = curry.anonymous
    goal = (self.P['=:='](a, 1), self.P['=:='](a, 2))
    self.assertEqual(self.values(goal), [(True, True)])
    self.assertEqual(curry.term((a, a)).free_vars, {})
    self.assertEqual(str(curry.term((a, a))), '(_a,_b)')

  def test_choice_structure_and_sharing(self):
    self.assertEqual(curry.choice(1, 2, 3), curry.choice(1, curry.choice(2, 3)))
    self.assertEqual(self.values(curry.choice(1, 2, 3)), [1, 2, 3])
    t = curry.choice(1, 2)
    self.assertEqual(self.values((t, t)), [(1, 1), (2, 2)])
    self.assertEqual(self.values((curry.choice(1, 2), curry.choice(1, 2))),
        [(1, 1), (1, 2), (2, 1), (2, 2)])
    self.assertEqual(self.values(curry.term(1).__choice__(2)), [1, 2])
    self.assertEqual(self.values(curry.term(1).__rchoice__(2)), [2, 1])

  def test_let_cycles_scopes_and_references(self):
    ones = curry.let(curry.ref('a'), a=self.P[':'](1, curry.ref('a')))
    self.assertEqual(self.values(self.P.take(3, ones)), [[1, 1, 1]])
    inner = curry.let(curry.ref('a'), a=2)
    outer = curry.let((curry.ref('a'), inner), a=1)
    self.assertEqual(self.values(outer), [(1, 2)])
    shared = curry.choice(1, 2)
    held = curry.let(curry.ref('a'), a=shared)
    self.assertEqual(self.values((shared, held)), [(1, 1), (2, 2)])
    self.assertEqual(self.values((held, shared)), [(1, 1), (2, 2)])
    with self.assertRaises(curry.CurryTypeError) as caught:
      curry.let(curry.ref('missing'), a=1)
    self.assertIn('a', str(caught.exception))
    with self.assertRaises(curry.CurryTypeError):
      curry.eval(curry.ref('a'))

  def test_dunders_and_infix_scope(self):
    t = curry.term(7)
    for expression, value in [(t + 2, 9), (2 + t, 9), (t - 2, 5),
        (9 - t, 2), (t * 2, 14), (2 * t, 14), (t / 2, 3.5),
        (14 / t, 2.0), (t // 2, 3), (14 // t, 2), (t % 2, 1),
        (14 % t, 0), (-t, -7), (curry.term(True) & False, False),
        (True & curry.term(False), False)]:
      self.assertEqual(self.values(expression), [value])
    C = curry.import_('Coin')
    self.assertEqual(str(C.inc(1) + 2 * C.coin), 'inc 1 + 2 * coin')
    self.assertEqual(str(curry.term([1]).__infix__('++', [2])), '[1] ++ [2]')
    self.assertIs(t.__infix__('missing', 1), NotImplemented)
    module = curry.compile('infixr 5 <+>\n(<+>) :: Int -> Int -> Int\nx <+> y = x + y\none :: Int\none = 1')
    g = module.one.__infix__('<+>', module.one)
    self.assertEqual(g.symbol.fixity, 'infixr 5')
    self.assertEqual(self.values(g), [2])
