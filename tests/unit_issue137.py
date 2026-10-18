'''Issue #137: the largest accepted tuple converts back to a Python tuple.'''
import cytest # from ./lib; must be first
import curry
import unittest


class TestIssue137(cytest.TestCase):
  def test_tuple_conversion_at_the_limit(self):
    for size in (14, 15):
      with self.subTest(size=size):
        value = tuple(range(size))
        signature = '(%s)' % ', '.join(['Int'] * size)
        self.assertEqual(curry.typeof(curry.term(value, type=signature)), signature)
        result = curry.eval(value).one()
        self.assertIs(type(result), tuple)
        self.assertEqual(result, value)
        self.assertEqual(curry.eval(curry.import_('Prelude').id(result)).one(), value)


if __name__ == '__main__':
  unittest.main()
