'''Issue #151: annotations and method applications respect the node's type.'''
import cytest # from ./lib; must be first
from curry.typecheck.errors import MismatchError
import curry, unittest

class TestIssue151(cytest.TestCase):
  def test_annotation_checks_recorded_type(self):
    P = cytest.raw.interp().prelude
    e = cytest.raw.expr(getattr(P, '+'), 1, typed=True)
    with self.assertRaises(MismatchError):
      cytest.raw.expr(cytest.raw.typed(e, 'Float -> Float'), typed=True)
    e = cytest.raw.expr(cytest.raw.typed(e, 'Int -> Int'), typed=True)
    self.assertEqual(list(curry.eval(cytest.raw.expr(P.apply, e, 2, typed=True))), [3])

  def test_missing_dictionary_at_construction(self):
    P = cytest.raw.interp().prelude
    with self.assertRaisesRegex(curry.CurryTypeError, 'dictionary'):
      e = cytest.raw.expr(P.apply, cytest.raw.expr(getattr(P, '+')), 1, typed=True)
      cytest.raw.expr(P.apply, e, 2, typed=True)

  def test_raw_missing_dictionary_in_child(self):
    code = '''
import cytest, curry
P = cytest.raw.interp().prelude
e = cytest.raw.expr(P.apply, cytest.raw.expr(P.apply, cytest.raw.expr(getattr(P, '+')), 1), 2)
# A function in the dictionary slot passes apply's representation check,
# but its result still must be a Num dictionary before the selector reads it.
bad_dict = cytest.raw.expr(getattr(P, '+'), cytest.raw.expr(P.id))
for goal in [e, cytest.raw.expr(P.apply, cytest.raw.expr(P.apply, bad_dict, 1), 2)]:
  try:
    list(cytest.raw.values(goal))
  except curry.EvaluationError as error:
    print(error)
'''
    proc = cytest.run_in_subprocess(code, 30, address_space=1 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.splitlines(), [
        'ill-typed application: expected a partial application'
      , 'ill-typed application: unexpected constructor type'
      ])

if __name__ == '__main__':
  unittest.main()
