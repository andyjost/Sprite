'''Issue #145: repr walks a long list without Python recursion.'''
import cytest # from ./lib; must be first
import curry
import unittest

class TestLongRepr(cytest.TestCase):
  def test_list_string_and_nested_list(self):
    for text in ('[1..500]', '([1..500],5)', 'replicate 500 \'a\''):
      value = next(curry.eval(curry.compile(text, mode='expr'), converter=None))
      shown = repr(value)
      self.assertIsInstance(shown, str)
      self.assertGreater(len(shown), 500)
      self.assertEqual(shown.count('<'), shown.count('>'))
      self.assertNotIn('...', shown)

class TestPublicPrinter(cytest.TestCase):
  def test_term_and_value_classes_share_str_and_show(self):
    P = curry.import_('Prelude')
    SF = curry.import_('Control.SetFunctions')
    var = curry.free('x')
    answer = curry.solve(P['=:='](var, 1)).one()
    objects = (P.Just(-1), curry.eval(P.Just(-1)).one(),
        curry.eval(P['+'](1)).one(),
        curry.eval(SF.set0(curry.choice(0, 1))).one(),
        var, answer, answer.bindings)
    for value in objects:
      with self.subTest(cls=type(value).__name__):
        self.assertEqual(curry.show(value), str(value))
    char = curry.Char('a')
    self.assertEqual(str(char), 'a')
    self.assertEqual(curry.show(char), "'a'")

if __name__ == '__main__':
  unittest.main()
