'''Bindings of held variables and consistent names across an answer.'''
import cytest
import curry
import unittest


class TestBindings(cytest.TestCase):
  def test_bound_and_reused(self):
    P = curry.import_('Prelude')
    v = curry.free()
    for n in (1, 2):
      a = curry.solve(P['=:='](v, n)).one()
      self.assertEqual(a.bindings[v], n)
      self.assertEqual(a.bindings['_a'], n)
      self.assertEqual(str(a), '{_a=%d} True' % n)
      self.assertEqual(dict(a.bindings), {'_a': n})
      self.assertEqual(list(a.bindings), ['_a'])
      self.assertEqual(len(a.bindings), 1)
      b = curry.solve(P['=:='](v, n)).one().bindings
      self.assertEqual(a.bindings, b)
      self.assertEqual(hash(a.bindings), hash(b))

  def test_order_identity_and_names(self):
    a, b, x = curry.free(), curry.free(), curry.free('x')
    answer = curry.solve((b, a, b, x)).one()
    self.assertEqual(list(answer.bindings), ['_a', '_b', 'x'])
    self.assertIs(answer.bindings[b], b)
    self.assertIs(answer.bindings[a], a)
    self.assertEqual(str(answer), '{_a=_a, _b=_b, x=x} (_a,_b,_a,x)')
    self.assertEqual(str(answer.bindings), '{_a=_a, _b=_b, x=x}')

  def test_unheld_and_collisions(self):
    a, x = curry.free(), curry.free('_a')
    answer = curry.solve((a, x, curry.anonymous, curry.anonymous)).one()
    self.assertEqual(str(answer), '{_b=_b, _a=_a} (_b,_a,_c,_d)')
    self.assertEqual(len(answer.bindings), 2)
    answer = curry.solve((curry.anonymous, curry.anonymous)).one()
    self.assertEqual(dict(answer.bindings), {})
    self.assertEqual(str(answer), '(_a,_b)')

  def test_distinct_unbound_binding_values(self):
    P = curry.import_('Prelude')
    x, y = curry.free(), curry.free()
    self.assertEqual(str(curry.solve(P['=:='](x, y)).one()),
        '{_a=_a, _b=_a} True')
    x, y = curry.free('x'), curry.free('y')
    a, b = curry.free(), curry.free()
    bindings = curry.Bindings([('x', a), ('y', b)], [x, y])
    self.assertEqual(str(bindings), '{x=_a, y=_b}')
    self.assertEqual(str(curry.Answer((b, a), bindings)),
        '{x=_a, y=_b} (_b,_a)')

  def test_shared_terms_in_constructed_answer(self):
    P = curry.import_('Prelude')
    x, y, a = curry.free('x'), curry.free('y'), curry.free()
    term = P.id(a)
    bindings = curry.Bindings([('x', (term, term)), ('y', term)], [x, y])
    self.assertEqual(str(bindings),
        '{x=let x1 = id _a in (x1,x1), y=id _a}')
    answer = curry.Answer(term, bindings)
    self.assertEqual(str(answer),
        '{x=let x1 = id _a in (x1,x1), y=id _a} id _a')

  def test_text_and_anonymous(self):
    P = curry.import_('Prelude')
    self.assertEqual(str(curry.solve(curry.parse('x =:= 1 where x free')).one()),
        '{x=1} True')
    self.assertEqual(dict(curry.solve(P['=:='](curry.anonymous, 1)).one().bindings), {})

  def test_holding_a_returned_variable(self):
    v = curry.eval(curry.anonymous).one()
    answer = curry.solve(v).one()
    self.assertEqual(list(answer.bindings), ['_a'])
    self.assertIs(answer.bindings[v], v)

  def test_alphabet(self):
    variables = [curry.free(type='Int') for _ in range(28)]
    answer = curry.solve(variables).one()
    self.assertEqual(list(answer.bindings)[-3:], ['_z', '_aa', '_ab'])


if __name__ == '__main__':
  unittest.main()
