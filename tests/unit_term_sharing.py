'''The text and fresh runtime graphs of shared terms.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect
from curry.backends.generic.eval import evaluator
from curry.objects.terms import _graph_key
from unittest.mock import patch
import os

FLOW_PATH = os.path.join(os.path.dirname(__file__), 'data', 'curry', 'flows')

class TestTermSharing(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)
    self.P = curry.import_('Prelude')
    self.C = curry.import_('Coin')

  def test_names_follow_first_occurrence(self):
    a, b = self.C.coin, self.C.inc(2)
    goal = curry.term((b, a, b, a))
    text = 'let x1 = inc 2; x2 = coin in (x1,x2,x1,x2)'
    self.assertEqual(str(goal), text)
    self.assertEqual(curry.show(goal), text)
    self.assertEqual(repr(goal), '<Term %s :: (Int, Int, Int, Int)>' % text)
    self.assertEqual(curry.show((a, a)), 'let x1 = coin in (x1,x1)')

  def test_nested_sharing_uses_one_root_let(self):
    c = self.C.coin
    inc = self.C.inc(c)
    goal = curry.term((inc, c, inc))
    text = 'let x1 = inc x2; x2 = coin in (x1,x2,x1)'
    self.assertEqual(str(goal), text)
    self.assertEqual(list(curry.eval(curry.parse(text, imports=[self.C]))),
        [(1, 0, 1), (2, 1, 2)])

  def test_generated_names_avoid_free_and_bound_names(self):
    c = self.C.coin
    x = curry.free('x1', type='Int')
    held = curry.let(curry.ref('x2'), x2=3)
    goal = curry.term((x, held, c, c))
    self.assertEqual(str(goal),
        'let x3 = coin in (x1,let x2 = 3 in x2,x3,x3)')
    self.assertEqual(curry.show((c, c)), 'let x1 = coin in (x1,x1)')

  def test_constructor_and_literal_sharing_prints_in_place(self):
    for t, text in [(self.P.Just(1), 'Just 1'), (curry.term(2), '2'),
        (curry.term([1, 2]), '[1,2]')]:
      with self.subTest(text=text):
        self.assertEqual(curry.show((t, t)), '(%s,%s)' % (text, text))

  def test_choice_parsed_and_partial_function_terms(self):
    for t, text in [(curry.choice(0, 1), '0 ? 1'),
        (curry.parse('coin', imports=[self.C]), 'coin'),
        (self.C.inc, 'inc'), (self.P.id(self.C.inc, 1), 'apply (id inc) 1')]:
      with self.subTest(text=text):
        self.assertEqual(curry.show((t, t)),
            'let x1 = %s in (x1,x1)' % text)

  def test_terms_inside_lists_keep_their_identity(self):
    c = self.C.coin
    xs = [c]
    self.assertEqual(curry.show((xs, xs)), 'let x1 = coin in ([x1],[x1])')
    self.assertEqual(curry.show((self.C.coin, self.C.coin)), '(coin,coin)')

  def test_eval_and_solve_build_fresh_shared_nodes(self):
    c = self.C.coin
    t = curry.term((c, c))
    before = str(t), repr(t), hash(t), _graph_key(t._node)
    roots, children = [], []
    evaluate = evaluator.evaluate
    def capture(interp, root):
      roots.append(root)
      left, right = [inspect.fwd_chain_target(a) for a in root.successors]
      self.assertEqual(left.id(), right.id())
      children.append(left)
      return evaluate(interp, root)
    with patch.object(evaluator, 'evaluate', capture):
      for _ in range(2):
        self.assertEqual(list(curry.eval(t)), [(0, 0), (1, 1)])
        self.assertEqual([a.value for a in curry.solve(t)], [(0, 0), (1, 1)])
        self.assertEqual((str(t), repr(t), hash(t), _graph_key(t._node)), before)
    self.assertEqual(len({root.id() for root in roots}), 4)
    self.assertEqual(len({child.id() for child in children}), 4)

  def test_parsed_let_shares_in_every_eval_and_solve(self):
    t = curry.parse('let c = coin in (c,c)', imports=[self.C])
    before = str(t), repr(t), hash(t), _graph_key(t._node)
    for _ in range(2):
      self.assertEqual(list(curry.eval(t)), [(0, 0), (1, 1)])
      self.assertEqual([a.value for a in curry.solve(t)], [(0, 0), (1, 1)])
      self.assertEqual((str(t), repr(t), hash(t), _graph_key(t._node)), before)

  def test_explicit_let_shares_in_every_eval_and_solve(self):
    t = curry.let((curry.ref('c'), curry.ref('c')), c=self.C.coin)
    for _ in range(2):
      self.assertEqual(list(curry.eval(t)), [(0, 0), (1, 1)])
      self.assertEqual([a.value for a in curry.solve(t)], [(0, 0), (1, 1)])

  def test_solve_bindings_and_term_survive_each_search(self):
    x = curry.free('x', type='Int')
    c = self.C.coin
    t = curry.term((self.P['=:='](x, c), x, c))
    before = str(t), repr(t), hash(t)
    for _ in range(2):
      answers = list(curry.solve(t))
      self.assertEqual([(a.value, dict(a.bindings)) for a in answers],
          [((True, 0, 0), {'x': 0}), ((True, 1, 1), {'x': 1})])
      self.assertEqual(list(curry.eval(t)), [(True, 0, 0), (True, 1, 1)])
      self.assertEqual((str(t), repr(t), hash(t)), before)

  def test_overlapping_and_closed_searches_are_independent(self):
    c = self.C.coin
    t = curry.term((c, c))
    first, second = curry.eval(t), curry.solve(t)
    self.assertEqual(next(first), (0, 0))
    self.assertEqual(next(second).value, (0, 0))
    first.close()
    self.assertEqual([a.value for a in second], [(1, 1)])
    self.assertEqual(list(curry.eval(t)), [(0, 0), (1, 1)])

  def test_internal_builders_keep_sharing(self):
    c = self.C.coin
    for build in (cytest.raw.expr, lambda *args, **kwds: cytest.raw.expr(*args, typed=True, **kwds)):
      node = build((c, c))
      self.assertEqual(list(curry.eval(node)),
          [(0, 0), (1, 1)])
