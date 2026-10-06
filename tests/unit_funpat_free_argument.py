'''
A functional pattern binds a free variable in its argument position.

A function with a functional pattern, called with a free variable where the
pattern is, binds the variable (Antoy and Hanus, "Declarative Programming
with Function Patterns", LOPSTR 2005): the pattern side ``c t1..tn``
against a free actual binds the variable to ``c x1..xn`` with fresh
variables and continues with the components, and a primitive value binds
the variable to the value.  The front end writes the match as ``=:<=``
with the pattern on the left, so the step of ``=:<=`` meets a constructor
or a value on the left and a free variable on the right.  Before the fix
the C++ runtime narrowed the variable over the constructors of the type,
which gave a Char node with no value for a Char, and the alternative died
(no value); the Python backend narrowed a builtin type with no values and
suspended.  ``=:=`` guided the narrowing to the constructor or the value
of the other side (make_guides of constr.cpp, constr_eq of constr.py), and
``=:<=`` now does the same.

The programs are in FunPatFreeArg.curry (the PAKCS oracle loads it) and
FunPatFreeArgSet.curry (the same read through set functions).  The
expected values are those of PAKCS 3.4.1.  Every goal is asked in two
ways: a text goal with ``where x free``, whose values carry the bindings,
and a set function over a function that creates the variable itself.  The
patterns cover a non-linear pattern over String, Int lists, Maybe and a
small data type, a primitive value of each builtin type (Char, Int inside
a list, Float), and a linear pattern.
'''
import cytest # from ./lib; must be first
from curry.typecheck.goals import Bindings
import curry, unittest

def values(*args, **kwds):
  '''The values of a goal, converted to Python.'''
  kwds.setdefault('converter', 'topython')
  return list(curry.eval(*args, **kwds))

def texts(*args):
  '''The values of a goal as Curry text.'''
  return [str(value) for value in curry.eval(*args)]

class TestFunPatFreeArgument(cytest.TestCase):
  def setUp(self):
    # cytest.TestCase resets curry after every test, so the modules are
    # imported for each one.
    self.M = curry.import_('FunPatFreeArg')
    self.S = curry.import_('FunPatFreeArgSet')

  def goal(self, text):
    '''A text goal over the module, with its where-free bindings.'''
    return curry.compile(text, mode='expr', imports=[self.M])

  # The rules over strings.
  # -----------------------
  RULES = [('rule', 'cc'), ('rule7', 'cc7'), ('rule8', 'cc8'), ('rule1', 'cc1')]

  def test_rules_ground(self):
    '''A ground call answers, and a mismatch has no value.'''
    for name, answer in self.RULES:
      f = getattr(self.M, name)
      self.assertEqual(values(f, 'vec.o', ['vec.c']), [answer], name)
      self.assertEqual(values(f, 'vec.o', ['other.c']), [], name)
      self.assertEqual(values(f, 'vec.o', []), [], name)

  def test_rules_free_argument(self):
    '''
    The free variable is bound by the functional pattern (rule), by its
    desugaring (rule7), by a constraint with the variable on the pattern
    side (rule8), and by the strict guard (rule1).  PAKCS: {ins=["vec.c"]}
    "cc", and so on; for rule8 it prints the binding unevaluated,
    {ins=["vec" ++ ".c"]}.
    '''
    for name, answer in self.RULES:
      goal = self.goal('%s "vec.o" ins where ins free' % name)
      self.assertEqual(
          values(goal), [Bindings(answer, {'ins': ['vec.c']})], name
        )
      self.assertEqual(texts(goal), ['{ins=["vec.c"]} "%s"' % answer], name)

  def test_rules_set_function(self):
    '''
    The same through a set function.  The variable is created inside cand,
    so the value of the set carries it bound.
    '''
    for name, answer in self.RULES:
      f = getattr(self.M, name)
      self.assertEqual(
          values(self.S.candidates, f, 'vec.o'), [[(['vec.c'], answer)]], name
        )
      self.assertEqual(values(self.M.cand, f, 'vec.o'), [(['vec.c'], answer)], name)

  # Other types.
  # ------------
  def test_int_list(self):
    '''The pattern [length xs] binds the free actual to [2].'''
    M, S = self.M, self.S
    self.assertEqual(values(M.count, [1, 2, 0], [2]), ['count'])
    self.assertEqual(values(M.count, [1, 2, 0], [3]), [])
    goal = self.goal('count [1,2,0] ins where ins free')
    self.assertEqual(values(goal), [Bindings('count', {'ins': [2]})])
    self.assertEqual(texts(goal), ['{ins=[2]} "count"'])
    self.assertEqual(values(M.countC, [1, 2, 0]), [([2], 'count')])
    self.assertEqual(values(S.countS, [1, 2, 0]), [[([2], 'count')]])

  def test_maybe(self):
    '''The pattern Just (n + 1) binds the free actual to Just 4.'''
    M, S = self.M, self.S
    Prelude = curry.getInterpreter().prelude
    self.assertEqual(values(M.wrap, 3, curry.expr(Prelude.Just, 4)), ['succ'])
    self.assertEqual(values(M.wrap, 3, curry.expr(Prelude.Nothing)), [])
    goal = self.goal('wrap 3 m where m free')
    self.assertEqual(texts(goal), ['{m=Just 4} "succ"'])
    self.assertEqual(texts(M.wrapC, 3), ['(Just 4, "succ")'])
    self.assertEqual(texts(S.wrapS, 3), ['[(Just 4, "succ")]'])

  def test_data_type(self):
    '''The pattern Rect (2 * r) (2 * r) binds the free actual to Rect 6 6.'''
    M, S = self.M, self.S
    circle = curry.expr(M.Circle, 3)
    self.assertEqual(values(M.double, circle, curry.expr(M.Rect, 6, 6)), ['rect'])
    self.assertEqual(values(M.double, circle, curry.expr(M.Rect, 6, 7)), [])
    goal = self.goal('double (Circle 3) t where t free')
    self.assertEqual(texts(goal), ['{t=Rect 6 6} "rect"'])
    self.assertEqual(texts(M.doubleC, circle), ['(Rect 6 6, "rect")'])
    self.assertEqual(texts(S.doubleS, circle), ['[(Rect 6 6, "rect")]'])

  def test_char(self):
    '''
    The pattern toUpper c, a primitive value, binds the free actual.  The
    type of ch, Char, occurs in the result type String, so the text of the
    plain goal depends on the where-free display rule of goals.py (Sprite
    leaves the variable in the value; PAKCS prints {ch='V'} "upper").  The
    rule has its own tests (unit_goals.py), so the plain goal checks the
    answer alone, and the pair pins the binding.
    '''
    M, S = self.M, self.S
    self.assertEqual(values(M.upper, 'vec', 'V'), ['upper'])
    self.assertEqual(values(M.upper, 'vec', 'v'), [])
    plain = texts(self.goal('upper "vec" ch where ch free'))
    self.assertEqual(len(plain), 1, plain)
    self.assertTrue(plain[0].endswith('"upper"'), plain)
    goal = self.goal('(ch, upper "vec" ch) where ch free')
    self.assertEqual(values(goal), [('V', 'upper')])
    self.assertEqual(texts(goal), ['(\'V\', "upper")'])
    self.assertEqual(values(M.upperC, 'vec'), [('V', 'upper')])
    self.assertEqual(values(S.upperS, 'vec'), [[('V', 'upper')]])

  def test_float(self):
    '''The pattern fromInt n / 2.0, a Float value, binds the free actual to 1.5.'''
    M, S = self.M, self.S
    self.assertEqual(values(M.half, 3, 1.5), ['half'])
    self.assertEqual(values(M.half, 3, 2.0), [])
    goal = self.goal('half 3 x where x free')
    self.assertEqual(values(goal), [Bindings('half', {'x': 1.5})])
    self.assertEqual(texts(goal), ['{x=1.5} "half"'])
    self.assertEqual(values(M.halfC, 3), [(1.5, 'half')])
    self.assertEqual(values(S.halfS, 3), [[(1.5, 'half')]])

  # A linear pattern.
  # -----------------
  def test_linear(self):
    '''
    The pattern Just (id 3) shares no variable with another argument.  The
    front end matches Just by a case, which narrows the free actual, and
    writes one =:<= for the sub-pattern, id 3 =:<= x, with no tuple and no
    shared variable: the Int value binds the component.
    '''
    M, S = self.M, self.S
    Prelude = curry.getInterpreter().prelude
    self.assertEqual(values(M.single, curry.expr(Prelude.Just, 3)), ['three'])
    self.assertEqual(values(M.single, curry.expr(Prelude.Just, 4)), [])
    self.assertEqual(values(M.single, curry.expr(Prelude.Nothing)), [])
    goal = self.goal('single m where m free')
    self.assertEqual(texts(goal), ['{m=Just 3} "three"'])
    self.assertEqual(texts(M.singleC), ['(Just 3, "three")'])
    self.assertEqual(texts(S.singleS), ['[(Just 3, "three")]'])

if __name__ == '__main__':
  unittest.main()
