'''Issue #108: shared empty lists in values do not share a recorded type.'''
import cytest # from ./lib; must be first
import curry
import unittest


class TestIssue108(cytest.TestCase):
  def test_values_with_empty_lists_at_two_types(self):
    P = curry.import_('Prelude')
    nested = curry.eval([[1, 2], [3]]).one()
    strings = curry.eval(['ab', 'c']).one()
    pair = curry.eval(([1], 'ab')).one()
    self.assertEqual(curry.typeof(nested), 'Num a => [[a]]')
    self.assertEqual(curry.typeof(strings), '[[Char]]')
    self.assertEqual(curry.typeof(pair), 'Num a => ([a], [Char])')
    self.assertEqual(curry.eval(P.concat(nested)).one(), [1, 2, 3])
    self.assertEqual(curry.eval(P.unwords(strings)).one(), 'ab c')
    self.assertEqual(curry.eval(P.fst(pair)).one(), [1])
    self.assertEqual(curry.eval(P.snd(pair)).one(), 'ab')

  def test_bare_empty_list_after_a_string_conversion(self):
    P = curry.import_('Prelude')
    nil = curry.eval([]).one()
    self.assertEqual(curry.eval(curry.term('')).one(), '')
    self.assertEqual(curry.typeof(nil), '[a]')
    self.assertEqual(curry.eval(P[':'](1, nil)).one(), [1])
    self.assertEqual(curry.eval((nil, 0)).one(), ([], 0))
    self.assertEqual(curry.eval(P.id((
        curry.term(nil, type='[Int]'), curry.term(nil, type='String')))).one(), ([], ''))


if __name__ == '__main__':
  unittest.main()
