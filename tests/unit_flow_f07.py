'''
F07: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_draw_on_demand: alt.py 9-11; output 1-4; lane 2.
  test_bare_iterator_is_consumed: alt.py 12-13, 23-24; output 5, 13; lane 2.
  test_term_remembers_iterator: alt.py 14-15, 21-22; output 6, 12; lane 2.
  test_empty_and_infinite_iterators: alt.py 16-17; output 7-8; lane 2.
  test_heterogeneous_iterator_rejected: alt.py 18; output 9; lane 2.
  test_bad_item_when_drawn: alt.py 19; output 10; lane 2.
  test_iterator_type_and_text: alt.py 20, 25; output 11, 14; lane 2.
  test_results_are_not_a_list: alt.py 27-31; output 15-18; lane 2.
  test_compound_and_string_items: alt.py 32-34; output 19-21; lane 2.
  test_bare_iterator_twice: alt.py 35; output 22; lane 2.

Left out: No semantic lines omitted. Generator prints become the drawn list assertion.

Departures and rules: Outputs 9-10 accept a heterogeneous list or raise EvaluationError.
Appendix A 5751-5753 and 6449-6450 require items at one element type and ConversionError
when drawn, so both tests require ConversionError. This is an open discrepancy beyond
the fixed one-letter-string facade defect. Conversion message wording is not frozen
(README approximation).

Lanes refer to the Python API implementation plan. Tests import curry,
the package. Missing proposed names are only used inside test methods.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import itertools

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestFlowF07(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_draw_on_demand(self):
    P = curry.import_('Prelude'); drawn = []
    def gen():
      for i in itertools.count(10):
        drawn.append(i)
        yield i
    t = P.take(3, gen())
    self.assertEqual(drawn, [])
    r = curry.eval(t)
    self.assertEqual(drawn, [])
    self.assertEqual(r.one(), [10, 11, 12])
    self.assertEqual(drawn, [10, 11, 12])

  def test_bare_iterator_is_consumed(self):
    P = curry.import_('Prelude'); it = iter([1, 2])
    self.assertEqual((curry.eval(P.length(it)).one(), curry.eval(P.length(it)).one(), list(it)), (2, 0, []))
    g = iter([1, 2, 3])
    self.assertEqual((curry.eval(P.length(g)).one(), curry.eval(P.length(g)).one()), (3, 0))

  def test_term_remembers_iterator(self):
    P = curry.import_('Prelude'); xs = curry.term(iter([1, 2]))
    self.assertEqual((curry.eval(P.length(xs)).one(), curry.eval(P.length(xs)).one()), (2, 2))
    t = P.length(iter([1, 2, 3]))
    self.assertEqual((curry.eval(t).one(), curry.eval(t).one()), (3, 3))

  def test_empty_and_infinite_iterators(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.eval(P.length(iter([]))).one(), 0)
    self.assertEqual(curry.eval(P.take(3, itertools.count())).one(), [0, 1, 2])

  def test_heterogeneous_iterator_rejected(self):
    P = curry.import_('Prelude')
    t = P.take(2, iter([1, 'a']))
    r = curry.eval(t)
    with self.assertRaises(curry.ConversionError):
      next(r)

  def test_bad_item_when_drawn(self):
    P = curry.import_('Prelude')
    t = P.foldr(P['+'], 0, iter([1, 'a']))
    r = curry.eval(t)
    with self.assertRaises(curry.ConversionError):
      next(r)

  def test_iterator_type_and_text(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.typeof(iter([1])), '[a]')
    self.assertEqual(str(P.take(3, iter([7, 8, 9]))), 'take 3 <iterator>')

  def test_results_are_not_a_list(self):
    P = curry.import_('Prelude'); C = curry.import_('Coin'); r = curry.eval(C.coin)
    self.assertIsInstance(r, curry.Results)
    with self.assertRaises(curry.ConversionError):
      P.length(r)
    self.assertEqual(curry.eval(P.length(list(r))).one(), 2)
    with self.assertRaises(curry.ConversionError):
      P.head(curry.eval(C.coin))

  def test_compound_and_string_items(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.eval(P.take(2, iter([[1], [2, 3]]))).one(), [[1], [2, 3]])
    self.assertEqual(curry.eval(P.length((c for c in 'ab'))).one(), 2)
    v = curry.eval(P.concat((c for c in 'ab'))).one()
    self.assertIs(type(v), str)
    self.assertEqual(v, 'ab')

  def test_bare_iterator_twice(self):
    g = iter([1, 2])
    self.assertEqual(curry.eval((g, g)).one(), ([1, 2], []))


if __name__ == '__main__':
  unittest.main()
