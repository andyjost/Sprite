'''Issue #114: a reused name runs its new code and old objects are stale.'''
import cytest # from ./lib; must be first
import curry
import unittest


class TestIssue114(cytest.TestCase):
  def test_same_name_after_reset_while_first_alive(self):
    first = curry.compile('f :: Int\nf = 1', name='SameB')
    old = first.f
    self.assertEqual(curry.eval(old).one(), 1)
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', name='SameB')
    self.assertEqual(curry.eval(second.f).one(), 2)
    with self.assertRaises(curry.StaleError):
      curry.eval(old).one()
    with self.assertRaises(curry.StaleError):
      first.f
    curry.reset()
    third = curry.compile('f :: Int\nf = 3', name='SameB')
    self.assertEqual(curry.eval(third.f).one(), 3)

  def test_reload_replaces_code_and_refuses_old_symbol(self):
    module = curry.compile('f :: Int\nf = 1', name='SameReload')
    old = module.f
    curry.reload(module, text='f :: Int\nf = 2')
    self.assertEqual(curry.eval(module.f).one(), 2)
    with self.assertRaises(curry.StaleError):
      curry.eval(old).one()


if __name__ == '__main__':
  unittest.main()
