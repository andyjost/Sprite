'''Issue #150: the raw list builder uses no Python recursion for its spine.'''
import cytest # from ./lib; must be first
from curry import inspect
import unittest

class TestIssue150(cytest.TestCase):
  def test_long_lists(self):
    for size in (1000, 100000):
      with self.subTest(size=size):
        node = cytest.raw.expr(list(range(size)))
        for value in range(size):
          self.assertTrue(inspect.isa_cons(node))
          self.assertEqual(node.successor(0).successor(0), value)
          node = node.successor(1)
        self.assertTrue(inspect.isa_nil(node))

if __name__ == '__main__':
  unittest.main()
