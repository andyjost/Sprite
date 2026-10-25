'''Issue #142: shared markers keep their type; raw equality checks its layout.'''
import cytest # from ./lib; must be first
import curry, unittest

class TestIssue142(cytest.TestCase):
  def test_marker_keeps_first_type(self):
    P = cytest.raw.interp().prelude
    eq = getattr(P, '=:=')
    x = cytest.raw.free()
    self.assertEqual(list(curry.eval(cytest.raw.expr(eq, x, [1], typed=True))), [True])
    with self.assertRaises(curry.CurryTypeError):
      cytest.raw.expr(eq, x, 1, typed=True)

  def test_public_variable_keeps_first_type(self):
    P = curry.import_('Prelude')
    x = curry.free()
    self.assertEqual(list(curry.eval(P['=:='](x, [1]))), [True])
    with self.assertRaises(curry.CurryTypeError):
      P['=:='](x, 1)

  def test_raw_equality_in_child(self):
    code = '''
import cytest, curry
P = cytest.raw.interp().prelude
for lhs, rhs in [([1], 1), (1, [1]), ([], False), (1, 1.0)]:
  try:
    list(cytest.raw.values(cytest.raw.expr(P.constrEq, lhs, rhs)))
  except curry.EvaluationError as error:
    print(error)
x = cytest.raw.free()
list(curry.eval(cytest.raw.expr(getattr(P, '=:='), x, [1], typed=True)))
try:
  list(cytest.raw.values(cytest.raw.expr(P.constrEq, x._shared(cytest.raw.interp()), 1)))
except curry.EvaluationError as error:
  print(error)
'''
    proc = cytest.run_in_subprocess(code, 30, address_space=1 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.splitlines(), ['ill-typed equality'] * 5)

if __name__ == '__main__':
  unittest.main()
