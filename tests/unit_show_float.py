'''
show of a Float prints one text on both backends, the text PAKCS prints
(issue #34).

The digits are the shortest that read back to the same value.  The point
stands in the digits when the value is at least 1.0e-4 and either below
1.0e15 or not integral; otherwise the text is d.ddde<exp>, where the
exponent carries its sign and no padding.  The Python show module and the
C++ runtime (graph/show.cpp) implement the rule; the Prelude's show reaches
one of them through prim_showFloatLiteral.
'''
import cytest # from ./lib; must be first
import curry, math
from curry import show as show_module

INF = float('inf')

# A value and its text.  PAKCS 3.4.1 printed the values of PAKCS this way.
# The values of OTHERS PAKCS cannot make: its front end reads a literal
# below the smallest normal float as 0.0 and loses digits of a long one, and
# an infinity or NaN raises an arithmetic error.  Their texts follow the
# same rule; Infinity, -Infinity, and NaN are written as KiCS2 writes them.
PAKCS = [
    (3.5, '3.5'), (1.0, '1.0'), (0.0, '0.0'), (-0.0, '-0.0'), (0.5, '0.5')
  , (0.1, '0.1'), (0.01, '0.01'), (0.001, '0.001'), (0.0001, '0.0001')
  , (1.0e-5, '1.0e-5'), (1.0e-7, '1.0e-7'), (1.23e-10, '1.23e-10')
  , (100.0, '100.0'), (1234.5678, '1234.5678'), (65536.0, '65536.0')
  , (1.0e6, '1000000.0'), (9999999.0, '9999999.0'), (1.0e7, '10000000.0')
  , (123456789.0, '123456789.0'), (1.0e15, '1.0e+15'), (1.0e16, '1.0e+16')
  , (1.0e21, '1.0e+21'), (1.0e22, '1.0e+22'), (1.0e100, '1.0e+100')
  , (9007199254740992.0, '9.007199254740992e+15'), (-2.5, '-2.5')
  , (math.sqrt(2.0), '1.4142135623730951'), (1.0 / 3.0, '0.3333333333333333')
  , (0.1 + 0.2, '0.30000000000000004')
  ]
OTHERS = [
    (123456789012345678.0, '1.2345678901234568e+17')
  , (1234567890123456.8, '1234567890123456.8')
  , (1.5e300, '1.5e+300'), (5.0e-324, '5.0e-324')
  , (2.2250738585072014e-308, '2.2250738585072014e-308')
  , (INF, 'Infinity'), (-INF, '-Infinity'), (float('nan'), 'NaN')
  ]
VALUES = PAKCS + OTHERS

CURRY = '''
showF :: Float -> String
showF x = show x

showL :: [Float] -> String
showL xs = show xs

showP :: Float -> String
showP x = showsPrec 11 x ""

addF :: Float -> Float -> String
addF x y = show (x + y)
'''

class TestShowFloat(cytest.TestCase):
  def test_show_float(self):
    '''The formatter of the Python show module.'''
    for value, text in VALUES:
      self.assertEqual(show_module.show_float(value), text, repr(value))

  def test_float_node(self):
    '''
    str and repr of a Float node.  str puts a negative value in parentheses.
    '''
    for value, text in VALUES:
      expected = '(%s)' % text if value < 0 else text
      self.assertEqual(str(curry.expr(value)), expected, repr(value))
      if value >= 0:
        self.assertEqual(
            repr(curry.expr(value)), '<Float %s>' % text, repr(value)
          )
    self.assertEqual(
        str(curry.expr([1.5, -2.5, 1.0e16])), '[1.5, (-2.5), 1.0e+16]'
      )

  def test_show_in_curry(self):
    '''
    show of the Prelude.  The values come from Python, so that the front end
    reads no literal: it loses the digits of 1.5e300 and reads 5.0e-324 as
    0.0.
    '''
    M = curry.compile(CURRY)
    for value, text in VALUES:
      self.assertEqual(
          next(curry.eval(M.showF, value, converter='topython')), text
        , repr(value)
        )
    self.assertEqual(
        next(curry.eval(M.showL, [1.5, -2.5, 1.0e16], converter='topython'))
      , '[1.5,-2.5,1.0e+16]'
      )
    self.assertEqual(
        next(curry.eval(M.showP, -2.5, converter='topython')), '(-2.5)'
      )
    self.assertEqual(
        next(curry.eval(M.addF, 0.1, 0.2, converter='topython'))
      , '0.30000000000000004'
      )

  def test_literals(self):
    '''show of literals the front end reads exactly; PAKCS prints the same.'''
    M = curry.compile('''
main :: String
main = show [3.5, 1.0, 0.0, 0.0001, 1.0e-5, 1.0e7, 1.0e15, 1.0e16, 0.1 + 0.2]
''')
    self.assertEqual(
        next(curry.eval(M.main, converter='topython'))
      , '[3.5,1.0,0.0,0.0001,1.0e-5,10000000.0,1.0e+15,1.0e+16,'
        '0.30000000000000004]'
      )
