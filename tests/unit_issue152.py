'''Issue #152: every demanded iterator item has the same element type.'''
import cytest # from ./lib; must be first
import curry, unittest

class TestIssue152(cytest.TestCase):
  def test_take_rejects_mixed_iterator(self):
    P = cytest.raw.interp().prelude
    goal = cytest.raw.expr(P.take, 2, iter([1, 'a']), typed=True)
    with self.assertRaisesRegex(curry.EvaluationError, 'cannot convert item'):
      list(curry.eval(goal))

  def test_foldr_context_fixes_element_type(self):
    P = cytest.raw.interp().prelude
    goal = cytest.raw.expr(P.foldr, getattr(P, '+'), 0, iter([1, 'a']), typed=True)
    with self.assertRaisesRegex(curry.EvaluationError, 'cannot convert item'):
      list(curry.eval(goal))

  def test_typeof_does_not_draw(self):
    drawn = []
    def source():
      for item in [1, 'a']:
        drawn.append(item)
        yield item
    P = curry.import_('Prelude')
    goal = P.take(2, source())
    self.assertEqual(curry.typeof(goal), '[a]')
    self.assertEqual(drawn, [])
    with self.assertRaisesRegex(curry.CurryTypeError, 'cannot convert item'):
      list(curry.eval(goal))

  def test_take_is_lazy(self):
    P = cytest.raw.interp().prelude
    goal = cytest.raw.expr(P.take, 1, iter([1, 'a']), typed=True)
    self.assertEqual(list(curry.eval(goal)), [[1]])

  def test_homogeneous_iterator(self):
    P = cytest.raw.interp().prelude
    goal = cytest.raw.expr(P.take, 2, iter([1, 2]), typed=True)
    self.assertEqual(list(curry.eval(goal)), [[1, 2]])

  def test_context_converts_items(self):
    goal = curry.term(iter([1, 2.5]), type='[Float]')
    self.assertEqual(curry.typeof(goal), '[Float]')
    self.assertEqual(list(curry.eval(goal)), [[1.0, 2.5]])

  def test_nested_items_share_one_type(self):
    P = cytest.raw.interp().prelude
    goal = cytest.raw.expr(P.take, 2, iter([[1], ['a']]), typed=True)
    with self.assertRaisesRegex(curry.EvaluationError, 'cannot convert item'):
      list(curry.eval(goal))

if __name__ == '__main__':
  unittest.main()
