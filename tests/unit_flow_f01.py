'''
F01: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_numbers: alt.py 14-15, 27; output 2-3, 14; lane 2.
  test_strings_and_rows: alt.py 16-20, 23; output 4-7, 10; lane 2.
  test_char_boundary: alt.py 21-22, 24; output 8-9, 11; lane 2.
  test_bool_is_not_int: alt.py 25-26; output 12-13; lane 2.
  test_maybe_boundary: alt.py 28-31, 33; output 15-18, 20; lane 2.
  test_range_is_a_list: alt.py 32; output 19; lane 2.
  test_empty_string: alt.py appendix 6414-6423; output decision (g); lane 1.

Left out: No semantic lines omitted. Harness lines 1-12 are replaced by unittest.

Departures and rules: Conversion messages are not frozen: the facade README marks them
approximations. The empty String case is added from decision (g), Appendix A 6414-6423.

Lanes refer to the Python API implementation plan. Tests import curry,
the package. Missing proposed names are only used inside test methods.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestFlowF01(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_numbers(self):
    P = curry.import_('Prelude'); C = curry.import_('Coin')
    x = curry.eval(C.inc(41)).one()
    y = curry.eval(P.sqrt(4)).one()
    z = curry.eval(P.fst((1.5, 'x'))).one()
    self.assertEqual((x, y, z), (42, 2.0, 1.5))
    self.assertIs(type(x), int)
    self.assertIs(type(y), float)
    self.assertIs(type(z), float)

  def test_strings_and_rows(self):
    P = curry.import_('Prelude'); S = curry.import_('Str')
    self.assertEqual(curry.eval(P.length('ab')).one(), 2)
    self.assertEqual(curry.eval(P.length('a')).one(), 1)
    self.assertEqual(curry.eval(P.unzip([(1, 'x'), (2, 'y')])).one(), ([1, 2], ['x', 'y']))
    rows = [('a', 1), ('b', 2)]
    self.assertEqual(curry.eval(S.names(rows)).one(), ['a', 'b'])
    self.assertEqual(curry.eval(S.names(curry.term(rows))).one(), ['a', 'b'])

  def test_char_boundary(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.ConversionError):
      P.ord('a')
    self.assertEqual(curry.eval(P.ord(curry.Char('a'))).one(), 97)
    c = curry.eval(P.chr(97)).one()
    self.assertIsInstance(c, curry.Char)
    self.assertEqual(c, 'a')

  def test_bool_is_not_int(self):
    P = curry.import_('Prelude')
    v = curry.eval(P['not'](True)).one()
    self.assertIs(v, False)
    with self.assertRaises(curry.ConversionError):
      P.chr(True)

  def test_maybe_boundary(self):
    P = curry.import_('Prelude'); C = curry.import_('Coin')
    with self.assertRaises(curry.ConversionError):
      P.maybe(0, C.inc, None)
    self.assertEqual(curry.eval(P.maybe(0, C.inc, P.Nothing)).one(), 0)
    self.assertEqual(curry.eval(P.maybe(0, C.inc, P.Just(5))).one(), 6)
    v = curry.eval(P.Just(5)).one()
    self.assertIsInstance(v, curry.Data)
    self.assertEqual(str(v), 'Just 5')
    self.assertEqual(v, P.Just(5))

  def test_range_is_a_list(self):
    P = curry.import_('Prelude')
    v = curry.eval(P.length(range(4))).one()
    self.assertIs(type(v), int)
    self.assertEqual(v, 4)

  def test_empty_string(self):
    O = curry.import_('Out')
    v = curry.eval(O.emptyString).one()
    self.assertIs(type(v), str)
    self.assertEqual(v, '')
    self.assertEqual(curry.show(v), '""')


if __name__ == '__main__':
  unittest.main()
