'''Issue #103: pair a Python free variable with each command it enables.'''
import cytest # from ./lib; must be first
import curry
import unittest

SOURCE = '''
rule :: String -> [String] -> String
rule "a" ["x"]      = "cmd1"
rule "a" ["y", "z"] = "cmd2"
rule (s ++ ".o") [s ++ ".c"] = "cc " ++ s
'''


class TestIssue103(cytest.TestCase):
  def test_python_variable_answers(self):
    M = curry.compile(SOURCE)
    ins = curry.free('ins')
    goal = M.rule('a', ins)
    self.assertEqual(list(curry.eval(goal)), ['cmd1', 'cmd2'])
    answers = list(curry.solve(goal))
    self.assertTrue(all(isinstance(a, curry.Answer) for a in answers))
    self.assertEqual([(a.value, a.bindings[ins]) for a in answers],
        [('cmd1', ['x']), ('cmd2', ['y', 'z'])])
    self.assertEqual([str(a) for a in answers],
        ['{ins=["x"]} "cmd1"', '{ins=["y","z"]} "cmd2"'])
    self.assertEqual([a.bindings['ins'] for a in answers], [['x'], ['y', 'z']])
    self.assertEqual(list(curry.eval((goal, ins))),
        [('cmd1', ['x']), ('cmd2', ['y', 'z'])])
    self.assertIs(curry.eval(ins).one(), ins)
    self.assertEqual(str(ins), 'ins')

  def test_text_variable_answers(self):
    M = curry.compile(SOURCE)
    answers = list(curry.solve(curry.parse('rule "a" ins where ins free', imports=[M])))
    self.assertEqual([(a.value, a.bindings['ins']) for a in answers],
        [('cmd1', ['x']), ('cmd2', ['y', 'z'])])


if __name__ == '__main__':
  unittest.main()
