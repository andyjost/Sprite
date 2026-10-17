'''Issue #143: an uncaught readFile error is a Curry file error.'''
import cytest # from ./lib; must be first
import curry
import unittest

class TestMissingFile(cytest.TestCase):
  def test_both_routes(self):
    P = curry.import_('Prelude')
    for goal in (P.readFile('/nosuch'), curry.parse('readFile "/nosuch"')):
      results = curry.eval(goal)
      with self.assertRaises(curry.CurryFileNotFoundError) as caught:
        next(results)
      self.assertIs(type(caught.exception), curry.CurryFileNotFoundError)
      self.assertIsInstance(caught.exception, FileNotFoundError)
      self.assertEqual(caught.exception.filename, '/nosuch')
      self.assertEqual(str(caught.exception), 'i/o error: No such file or directory: /nosuch')
      self.assertEqual(list(results), [])

if __name__ == '__main__':
  unittest.main()
