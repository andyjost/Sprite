'''
F11: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_values_collection: alt.py 5; output 2; lane 3.
  test_empty_set_is_a_value: alt.py 6-7; output 3; lane 3.
  test_argument_choice_outside: alt.py 8-9; output 4-5; lane 3.
  test_nested_sets_and_multiplicity: alt.py 10-11; output 6-7; lane 3.
  test_free_argument_answers: alt.py 12-15; output 8-9; lane 3.
  test_captured_iterator: alt.py 16-17; output 10; lane 2.
  test_weak_encapsulation: alt.py 18-21; output 11-13; lane 4.
  test_set_term_printing: alt.py 22; output 14; lane 4.

Left out: No semantic lines omitted. Python repr of anonymous variables at 15 is checked
as nested lists of Var objects, without global repr counters.

Departures and rules: No value departures. The weak encapsulation of output 12 is
expressly kept by Appendix A 6159-6172 and the owner decision, despite the facade README
calling the earlier strong-capture law unimplemented.

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


class TestFlowF11(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_values_collection(self):
    SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets')
    vs = curry.eval(SF.set0(S.coin)).one()
    self.assertIsInstance(vs, curry.Values)
    self.assertEqual(str(vs), 'Values [0,1]')
    self.assertEqual(sorted(vs), [0, 1])
    self.assertEqual(len(vs), 2)
    self.assertIn(1, vs)

  def test_empty_set_is_a_value(self):
    P = curry.import_('Prelude'); SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets')
    e = curry.eval(SF.set2(S.rule, 'b', ['x'])).one()
    self.assertEqual(str(curry.eval(SF.set2(S.rule, 'a', ['x'])).one()), 'Values ["cmd1"]')
    self.assertEqual(sorted(e), [])
    self.assertFalse(e)
    self.assertEqual(e, curry.eval(SF.set0(P.failed)).one())

  def test_argument_choice_outside(self):
    SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets')
    self.assertEqual([sorted(v) for v in curry.eval(SF.set1(S.inc, S.coin))], [[1], [2]])
    self.assertEqual(list(curry.eval(SF.set1(S.inc, S.nothing))), [])

  def test_nested_sets_and_multiplicity(self):
    SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets')
    self.assertEqual(curry.eval(S.nested).one(), [[0, 1]])
    self.assertEqual(curry.eval(S.twice).one(), [0, 1, 1, 2])
    tw = curry.eval(SF.set0(S.coin + S.coin)).one()
    self.assertEqual(str(tw), 'Values [0,1,1,2]')
    self.assertEqual(list(tw), [0, 1, 1, 2])
    self.assertEqual(sorted(tw), [0, 1, 1, 2])

  def test_free_argument_answers(self):
    SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets'); x = curry.free('x')
    answers = list(curry.solve(SF.set2(S.rule, 'a', x)))
    self.assertEqual(len(answers), 11)
    self.assertEqual([str(a) for a in answers], [
        '{x=[]} Values []'
      , '{x="":_a} Values []'
      , '{x=(_a:_b:_c):_d} Values []'
      , '{x=(_a:_b:_c):_d} Values []'
      , '{x=[_a]:_b:_c} Values []'
      , '{x=[[_a]]} Values ["cmd1"]'
      , '{x=[[_a]]} Values []'
      , '{x=[_a]:"":_b} Values []'
      , '{x=[_a]:(_b:_c:_d):_e} Values []'
      , '{x=[_a]:[_b]:_c:_d} Values []'
      , '{x=[[_a],[_b]]} Values ["cmd2"]'
      ])
    nonempty = [(sorted(a.value), a.bindings[x]) for a in answers if a.value]
    self.assertEqual([v for v, _ in nonempty], [['cmd1'], ['cmd2']])
    self.assertEqual([len(rows) for _, rows in nonempty], [1, 2])
    for _, rows in nonempty:
      for row in rows:
        self.assertEqual(len(row), 1)
        self.assertIsInstance(row[0], curry.Var)

  def test_captured_iterator(self):
    P = curry.import_('Prelude'); SF = curry.import_('Control.SetFunctions')
    it = iter([1, 2, 3]); xs = curry.term(it)
    self.assertEqual(sorted(curry.eval(SF.set1(P.length, xs)).one()), [3])
    self.assertEqual(list(it), [])

  def test_weak_encapsulation(self):
    SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets'); t = S.coin
    self.assertEqual([sorted(v) for v in curry.eval(SF.set0(t))], [[0, 1]])
    self.assertEqual([(sorted(v), c) for v, c in curry.eval((SF.set0(t), t))], [([0, 1], 0), ([0, 1], 1)])
    self.assertEqual([(c, sorted(v)) for c, v in curry.eval((t, SF.set0(t)))], [(0, [0]), (1, [1])])
    self.assertEqual(str(t), 'coin')

  def test_set_term_printing(self):
    SF = curry.import_('Control.SetFunctions'); S = curry.import_('Sets')
    self.assertEqual(repr(SF.set0(S.coin)), '<Term set0 coin :: Values Int>')
    self.assertEqual(str(SF.set2(S.rule, 'a', ['x'])), 'set2 rule "a" ["x"]')
    self.assertEqual(curry.typeof(SF.set0(S.coin)), 'Values Int')


if __name__ == '__main__':
  unittest.main()
